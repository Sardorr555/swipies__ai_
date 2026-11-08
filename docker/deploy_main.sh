#!/usr/bin/env bash
# Deploy an exact reviewed commit to the existing Swipies installation.
set -Eeuo pipefail
umask 077
target=${1:?Expected a full commit SHA}
[[ "$target" =~ ^[0-9a-f]{40}$ ]] || exit 2
cd "$HOME/swipies__ai_"
exec 200>.git/swipies-deploy.lock
if ! flock -n 200; then
  echo 'Another deployment is active; inspecting processes holding lock:'
  fuser -v .git/swipies-deploy.lock 2>&1 || true
  echo 'Attempting to terminate stale orphaned deployment process...'
  fuser -k -9 .git/swipies-deploy.lock 2>/dev/null || true
  sleep 2
  flock -n 200 || { echo 'Deployment lock still held; aborting'; exit 1; }
  echo 'Stale deployment lock successfully cleared'
fi
git cat-file -e "$target^{commit}"
git diff --quiet --ignore-submodules=all && git diff --cached --quiet --ignore-submodules=all || {
  echo 'Tracked server changes must be reviewed before deployment'
  echo 'Unstaged tracked paths and change sizes (file contents are not printed):'
  git diff --stat --ignore-submodules=all
  git diff --summary --ignore-submodules=all
  echo 'Staged tracked paths and change sizes (file contents are not printed):'
  git diff --cached --stat --ignore-submodules=all
  git diff --cached --summary --ignore-submodules=all
  exit 1;
}
previous=$(git rev-parse HEAD)
stamp=$(date -u +%Y%m%dT%H%M%SZ)-${target:0:12}
state="$HOME/swipies-deployments/$stamp"
mkdir -p "$state"
printf '%s\n' "$previous" > "$state/previous-commit"
printf '%s\n' "$target" > "$state/target-commit"
git update-ref "refs/swipies/rollback/$stamp" "$previous"
compose() { sudo docker compose -f docker/docker-compose.yml --profile cpu --profile elasticsearch --profile metadata-mysql "$@"; }
compose config --quiet
for name in swipies-mysql swipies-redis swipies-es01 swipies-minio swipies-cpu swipies-frontend; do
  [[ $(sudo docker inspect --format '{{.State.Running}}' "$name") == true ]] || {
    echo "Required existing service is down: $name"; exit 1;
  }
done
cpu_image=$(sudo docker inspect --format '{{.Image}}' swipies-cpu)
web_image=$(sudo docker inspect --format '{{.Image}}' swipies-frontend)
sudo docker image tag "$cpu_image" "swipies-rollback-cpu:$stamp"
sudo docker image tag "$web_image" "swipies-rollback-frontend:$stamp"
cat > "$state/rollback-images.yml" <<EOF
services:
  ragflow-cpu:
    image: swipies-rollback-cpu:$stamp
  frontend:
    image: swipies-rollback-frontend:$stamp
EOF
echo 'Saving private database snapshot before updating code'
sudo docker exec swipies-mysql sh -c 'exec mysqldump --user=root --password="$MYSQL_ROOT_PASSWORD" --all-databases --single-transaction --routines --events --no-tablespaces --set-gtid-purged=OFF' > "$state/mysql.sql" 2> "$state/mysql-backup.log"
test -s "$state/mysql.sql"
echo "Rollback reference: refs/swipies/rollback/$stamp"
echo "Private backups: $state"
changed=false
restarted=false
finish() {
  rc=$?
  trap - EXIT
  if (( rc != 0 )) && [[ $changed == true ]]; then
    echo 'Deployment failed; restoring previous code and application images'
    if git checkout --detach "$previous" > "$state/rollback-git.log" 2>&1; then
      if [[ $restarted == true ]]; then
        sudo docker compose -f docker/docker-compose.yml -f "$state/rollback-images.yml" --profile cpu --profile elasticsearch --profile metadata-mysql up -d --no-deps --no-build --force-recreate ragflow-cpu frontend > "$state/rollback.log" 2>&1 || echo 'Application rollback needs operator attention; inspect private rollback.log'
      fi
    else
      echo 'Code rollback needs operator attention; inspect private rollback-git.log'
    fi
  fi
  sudo rm -f /tmp/swipies_deploying.lock
  exit "$rc"
}
sudo touch /tmp/swipies_deploying.lock
trap finish EXIT
# Only a clean checkout is replaced; .env, data volumes and other services stay intact.
changed=true
git checkout --detach "$target"
compose config --quiet
echo 'Building frontend while the existing containers remain running'
# Ensure sufficient swap space and free page caches so Docker build has headroom alongside running containers
if [[ $(swapon --show | wc -l) -le 1 ]]; then
  if [[ ! -f /swapfile_deploy ]]; then
    sudo fallocate -l 6G /swapfile_deploy 2>/dev/null || sudo dd if=/dev/zero of=/swapfile_deploy bs=1M count=6144 2>/dev/null || true
    sudo chmod 600 /swapfile_deploy 2>/dev/null || true
    sudo mkswap /swapfile_deploy 2>/dev/null || true
  fi
  sudo swapon /swapfile_deploy 2>/dev/null || true
fi
sync; sudo sysctl -w vm.drop_caches=3 2>/dev/null || true
( while true; do sleep 25; echo "[deploy heartbeat $(date -u +%T)] compiling frontend assets..."; done ) &
heartbeat_pid=$!
compose build frontend 2>&1 | tee "$state/build.log" || { kill "$heartbeat_pid" 2>/dev/null || true; echo 'Build failed; inspect private build.log'; exit 1; }
kill "$heartbeat_pid" 2>/dev/null || true
wait "$heartbeat_pid" 2>/dev/null || true
echo 'Updating only Swipies application containers'
restarted=true
compose up -d --no-deps --no-build --force-recreate ragflow-cpu frontend > "$state/start.log" 2>&1 || { echo 'Container start failed; inspect private start.log'; exit 1; }
ready=false
for attempt in {1..60}; do
  if sudo docker exec swipies-cpu python -c 'import json,urllib.request; r=json.load(urllib.request.urlopen("http://127.0.0.1:9380/api/v1/agent-access/manifest",timeout=5)); assert r["name"]=="Swipies Agent Access" and r["version"]=="1.0.0"' >/dev/null 2>&1; then
    ready=true; break
  fi
  sleep 5
done
[[ $ready == true ]] || { echo 'Agent Access health check failed'; exit 1; }
sudo docker exec swipies-frontend wget -q -O /dev/null http://127.0.0.1/
printf '%s\n' "$target" > "$state/successful-commit"
echo "Deployed and locally healthy: $target"
echo 'Public HTTPS and authenticated end-to-end verification are still required'
