import os
import subprocess
import sys

def load_env():
    env = {}
    env_path = ".env"
    if not os.path.exists(env_path):
        print(".env file not found", flush=True)
        return env
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if val.startswith('"') and val.endsWith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endsWith("'"):
                    val = val[1:-1]
                env[key] = val
    return env

def main():
    env = load_env()
    keys_to_sync = [
        'TELEGRAM_BOT_TOKEN',
        'MONGO_URI',
        'GEMINI_API_KEY',
        'ALLOWED_CHAT_ID',
        'GEMINI_MODEL'
    ]
    
    print("Syncing production environment variables to Vercel...", flush=True)
    for key in keys_to_sync:
        value = env.get(key)
        if not value:
            print(f"Warning: {key} is not defined in .env, skipping.", flush=True)
            continue
            
        print(f"Setting {key} on production...", flush=True)
        try:
            # Add environment variable with --force and --yes
            cmd = f'vercel env add "{key}" production --value "{value}" --yes --force'
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if p.returncode == 0:
                print(f"Successfully updated {key} on production.", flush=True)
            else:
                # Mask value in error printing if any
                err_output = p.stderr.replace(value, "******") if value else p.stderr
                stdout_output = p.stdout.replace(value, "******") if value else p.stdout
                print(f"Failed to update {key}: {stdout_output} {err_output}", flush=True)
        except Exception as e:
            print(f"Error updating {key}: {e}", flush=True)

if __name__ == "__main__":
    main()
