import os
import subprocess

def main():
    vars_to_set = []
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            # Remove inline comments
            if "#" in line:
                line = line.split("#")[0].strip()

            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                # Quote value for shell
                vars_to_set.append(f'{k}="{v}"')
    
    if not vars_to_set:
        print("No variables found.")
        return

    # Join them space separated
    if not vars_to_set:
        print("No variables found.")
        return

    print(f"Setting {len(vars_to_set)} variables one by one...")
    for item in vars_to_set:
        cmd = f"railway variables --set {item}"
        print(f" > {item.split('=')[0]}...") 
        subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    main()
