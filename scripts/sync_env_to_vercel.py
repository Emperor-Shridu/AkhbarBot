import os
import subprocess

def load_env():
    env = {}
    env_path = ".env"
    if not os.path.exists(env_path):
        print(".env file not found")
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
    
    print("Syncing environment variables to Vercel...")
    for key in keys_to_sync:
        value = env.get(key)
        if not value:
            print(f"Warning: {key} is not defined in .env, skipping.")
            continue
            
        for target in ['production', 'preview']:
            print(f"Updating {key} for {target}...")
            try:
                # Remove first if already exists to avoid conflict
                cmd_rm = ["powershell", "-ExecutionPolicy", "Bypass", "-Command", f"vercel env rm {key} {target} -y"]
                subprocess.run(cmd_rm, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Add environment variable
                cmd_add = ["powershell", "-ExecutionPolicy", "Bypass", "-Command", f"vercel env add {key} {target} --value '{value}' --yes"]
                p = subprocess.run(cmd_add, capture_output=True, text=True)
                if p.returncode == 0:
                    print(f"Successfully updated {key} for {target}.")
                else:
                    print(f"Failed to update {key} for {target}: {p.stdout} {p.stderr}")
            except Exception as e:
                print(f"Error updating {key} for {target}: {e}")

if __name__ == "__main__":
    main()
