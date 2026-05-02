import subprocess
import sys


def run_cmd(cmd):
    print(f"\n➡️ Running: {cmd}")

    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 Starting deployment script...")

    # 1. Reset local changes
    run_cmd("git reset --hard")

    # 2. Pull latest code
    run_cmd("git pull origin ws-order-feed")

    # 3. Ensure permissions
    run_cmd("chmod +x stop_app.sh start_app.sh")

    print("\n✅ Deployment commands executed successfully")