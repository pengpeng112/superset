#!/usr/bin/env bash
# 生产日常巡检一键体检（20261120-RBAC-BACKEND 批升 18 项）。只读：不重启、不写库、不改配置。
# 供信息科随时执行：bash /home/superset/superset_home/scripts/superset_health_check.sh
# 检查项：六容器 / 磁盘 / HIS 隧道 15215 / 02:00 备份(DONE+SHA256) / 06:00 同步 rc /
#         06:15 缓存预热(耗时+成功率) / nginx.conf 挂载一致 / 5 个核心 JS 版本与 SHA256 /
#         9. RBAC 恒常（11 角色矩阵 / Gamma 仅外壳34 / 绑定63 / 授权66 / 受保护在位 / 序列无滞后）
# 退出码：0 全绿；1 存在红项（⚠ 不影响退出码）。
set -u
G=0; R=0
ok(){ printf '  [绿] %s\n' "$1"; G=$((G+1)); }
bad(){ printf '  [红] %s\n' "$1"; R=$((R+1)); }
warn(){ printf '  [黄] %s\n' "$1"; }
hdr(){ printf '\n== %s ==\n' "$1"; }

cd /home/superset || { echo "无法进入 /home/superset"; exit 1; }

hdr "1. 六容器运行状态"
for c in superset-nginx superset-web superset-worker superset-beat superset-postgres superset-redis; do
  st=$(docker ps --filter "name=^${c}$" --format '{{.Status}}' 2>/dev/null)
  if [ -z "$st" ]; then
    bad "$c 未在运行"
  elif echo "$st" | grep -q '(healthy)'; then
    ok "$c $st"
  elif echo "$st" | grep -qE '\(unhealthy\)|Restarting'; then
    bad "$c $st"
  else
    # beat/worker/nginx 无健康检查探针，Up 即视为正常
    ok "$c $st（无探针，按 Up 判定）"
  fi
done

hdr "2. 磁盘使用率"
df -h / | awk 'NR==2{u=$5}END{exit !(u+0<80)}' && ok "根分区使用率 $(df -h / | awk 'NR==2{print $5}')（<80%）" || {
  u=$(df -h / | awk 'NR==2{print $5+0}')
  if [ "$u" -ge 90 ]; then bad "根分区使用率 ${u}%（≥90%，请立即清理）"; else warn "根分区使用率 ${u}%（≥80%，请关注）"; fi
}

hdr "3. HIS 隧道（15215）"
tun=$(systemctl is-active his-tunnel 2>/dev/null)
if [ "$tun" = "active" ] && ss -ltn 2>/dev/null | grep -q ':15215 '; then
  ok "his-tunnel=active，0.0.0.0:15215 已监听"
else
  bad "his-tunnel=${tun:-unknown} / 15215 未监听（systemctl restart his-tunnel）"
fi

hdr "4. 最近 02:00 数据库备份"
latest=$(ls -1t backup/gens/ 2>/dev/null | grep -v '^latest$' | head -1)
if [ -z "$latest" ]; then
  bad "backup/gens/ 下无备份目录"
else
  d="backup/gens/$latest"
  if [ ! -f "$d/DONE" ]; then
    bad "$latest 无 DONE 标识（备份可能未完成）"
  else
    want=$(grep -oP '^sha256=\K[0-9a-f]+' "$d/manifest.txt" 2>/dev/null)
    dump=$(grep -oP '^dump=\K\S+' "$d/manifest.txt" 2>/dev/null)
    if [ -z "$want" ] || [ -z "$dump" ]; then
      bad "$latest manifest.txt 缺 sha256/dump 字段"
    elif [ ! -f "$d/$dump" ]; then
      bad "$latest dump 文件缺失：$dump"
    else
      got=$(sha256sum "$d/$dump" | awk '{print $1}')
      if [ "$got" = "$want" ]; then
        sz=$(du -h "$d/$dump" | awk '{print $1}')
        obj=$(grep -oP '^live_objects\(slices/dashboards\)_at_dump=\K\S+' "$d/manifest.txt")
        ok "$latest DONE 且 SHA256 一致（$dump $sz${obj:+，对象 $obj}）"
      else
        bad "$latest SHA256 不一致（manifest=$want 实测=$got）"
      fi
    fi
  fi
fi

hdr "5. 最近 06:00 用户同步"
last_sync=$(grep 'end exit=' logs/sync.log 2>/dev/null | tail -1)
if [ -z "$last_sync" ]; then
  bad "logs/sync.log 无 end exit= 记录"
elif echo "$last_sync" | grep -q 'exit=0'; then
  ok "$last_sync"
else
  bad "$last_sync"
fi

hdr "6. 最近 06:15 缓存预热"
last_sum=$(grep -o 'SUMMARY json=.*' logs/warmup.log 2>/dev/null | tail -1)
if [ -z "$last_sum" ]; then
  warn "logs/warmup.log 尚无 SUMMARY（今天 06:15 首次运行后出现；也可手动跑 run_warmup.sh）"
else
  total=$(echo "$last_sum" | grep -o '"total": *[0-9]*' | grep -o '[0-9]*')
  okn=$(echo "$last_sum" | grep -o '"ok": *[0-9]*' | grep -o '[0-9]*')
  secs=$(echo "$last_sum" | grep -o '"duration_secs": *[0-9.]*' | grep -o '[0-9.]*')
  cb=$(echo "$last_sum" | grep -o '"circuit_break": *[a-z]*' | grep -o 'true\|false')
  run_ts=$(grep ' start ' logs/warmup.log | tail -1 | cut -d']' -f1 | tr -d '[')
  if [ "${cb:-true}" = "false" ] && [ "$okn" = "$total" ] && [ "${total:-0}" -gt 0 ]; then
    ok "最近一次${run_ts:+ $run_ts}命中 ${okn}/${total}，耗时 ${secs}s，无熔断"
  else
    bad "最近一次预热异常：ok=${okn:-?}/${total:-?} 耗时=${secs:-?}s 熔断=${cb:-?}（查 logs/warmup.log）"
  fi
fi

hdr "7. nginx.conf 挂载一致性"
host_sha=$(sha256sum nginx.conf 2>/dev/null | awk '{print $1}')
ctr_sha=$(docker exec superset-nginx sha256sum /etc/nginx/conf.d/default.conf 2>/dev/null | awk '{print $1}')
inode=$(stat -c %i nginx.conf 2>/dev/null)
if [ -n "$host_sha" ] && [ "$host_sha" = "$ctr_sha" ]; then
  ok "宿主机与容器内 nginx.conf 一致（sha=${host_sha:0:12}…，inode=$inode）"
else
  bad "nginx.conf 不一致！宿主=${host_sha:-读取失败} 容器=${ctr_sha:-读取失败}（宿主文件被重建后容器仍挂旧文件，需 docker restart superset-nginx）"
fi

hdr "8. 生产 5 个核心 JS 版本与 SHA256"
miss=0
for js in report-guards report-dates report-ui home-ui monthly-report; do
  ver=$(grep -o "${js}.js?v=[0-9A-Za-z]*" nginx.conf | head -1 | sed "s/.*v=//")
  sha=$(sha256sum "custom/${js}.js" 2>/dev/null | awk '{print substr($1,1,12)}')
  if [ -n "$ver" ] && [ -n "$sha" ]; then
    ok "${js}.js  v=$ver  sha256=${sha}…"
  else
    bad "${js}.js 版本串或文件缺失（nginx.conf ver=${ver:-无}）"; miss=1
  fi
done

hdr "9. RBAC 恒常（20261120 批次终态）"
PGPW=$(grep -E '^POSTGRES_PASSWORD=' .env | head -1 | cut -d= -f2-)
rbac_line=$(docker exec -e PGPASSWORD="$PGPW" superset-postgres psql -U superset -d superset -tA -F'|' -c "
SELECT
  (SELECT count(*) FROM ab_role WHERE name LIKE '报表授权_%') AS rbac_roles,
  (SELECT count(*) FROM dashboard_roles dr JOIN ab_role r ON r.id=dr.role_id WHERE r.name='Gamma' AND dr.dashboard_id<>34) AS gamma_extra,
  (SELECT count(*) FROM dashboard_roles) AS dr_rows,
  (SELECT count(*) FROM ab_permission_view_role pvr JOIN ab_permission_view pv ON pv.id=pvr.permission_view_id JOIN ab_permission p ON p.id=pv.permission_id JOIN ab_view_menu vm ON vm.id=pv.view_menu_id WHERE p.name='datasource_access' AND vm.name ~ '\(id:[0-9]+\)$') AS ds_access,
  (SELECT count(*) FROM ab_user_role ur JOIN ab_user u ON u.id=ur.user_id JOIN ab_role r ON r.id=ur.role_id WHERE u.username='001283' AND r.name='报表授权_病案离院明细') AS prot1,
  (SELECT count(*) FROM ab_user_role ur JOIN ab_user u ON u.id=ur.user_id JOIN ab_role r ON r.id=ur.role_id WHERE u.username='001643' AND r.name='报表授权_抗菌办') AS prot2,
  (SELECT last_value FROM ab_user_role_id_seq) - (SELECT coalesce(max(id),0) FROM ab_user_role) AS seq1,
  (SELECT last_value FROM ab_role_id_seq) - (SELECT coalesce(max(id),0) FROM ab_role) AS seq2,
  (SELECT last_value FROM ab_permission_view_role_id_seq) - (SELECT coalesce(max(id),0) FROM ab_permission_view_role) AS seq3,
  (SELECT last_value FROM ab_view_menu_id_seq) - (SELECT coalesce(max(id),0) FROM ab_view_menu) AS seq4,
  (SELECT last_value FROM ab_permission_view_id_seq) - (SELECT coalesce(max(id),0) FROM ab_permission_view) AS seq5
" 2>/dev/null)
if [ -z "$rbac_line" ]; then
  bad "RBAC 恒常查询失败（postgres 容器或 .env POSTGRES_PASSWORD 异常）"
else
  IFS='|' read -r n_roles gamma_extra dr_rows ds_access prot1 prot2 s1 s2 s3 s4 s5 <<EOF
$rbac_line
EOF
  if [ "$n_roles" = "11" ] && [ "$gamma_extra" = "0" ] && [ "$dr_rows" = "63" ] \
     && [ "$ds_access" = "66" ] && [ "$prot1" = "1" ] && [ "$prot2" = "1" ] \
     && [ "$s1" -ge 0 ] && [ "$s2" -ge 0 ] && [ "$s3" -ge 0 ] && [ "$s4" -ge 0 ] && [ "$s5" -ge 0 ]; then
    ok "RBAC 恒常：11 角色 / Gamma 仅外壳34 / 绑定 63 / 授权 66 / 受保护在位 / 5 序列无滞后（超前 +$s1）"
  else
    bad "RBAC 恒常异常：角色=$n_roles Gamma外看板=$gamma_extra 绑定=$dr_rows 授权=$ds_access 受保护=$prot1/$prot2 序列差=$s1/$s2/$s3/$s4/$s5（详见 全院角色矩阵与科室赋权操作手册.md 排障节）"
  fi
fi

printf '\n========== 体检汇总：绿 %d / 红 %d ==========\n' "$G" "$R"
[ "$R" -eq 0 ] && echo "全部通过 ✔" || echo "存在红项，请按上文提示处理 ✘"
exit $([ "$R" -eq 0 ] && echo 0 || echo 1)
