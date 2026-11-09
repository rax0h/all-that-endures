set -euo pipefail
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /usr/share/swift /usr/local/.ghcup /usr/local/share/powershell
sudo docker image prune -af
df -h . > evidence/disk-start.txt

