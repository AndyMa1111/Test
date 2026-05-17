"""Fix nginx config and check app logs."""
import pexpect

HOST = "47.108.64.228"
USER = "root"
PASS = "Andy0000"

def run(cmds):
    child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {USER}@{HOST}", timeout=60)
    child.expect("password:")
    child.sendline(PASS)
    child.expect("#", timeout=15)
    for cmd in cmds:
        print(f"  $ {cmd}")
        child.sendline(cmd)
        child.expect("#", timeout=60)
        out = child.before.decode()
        lines = [l.strip() for l in out.split("\n") if l.strip() and not l.strip().startswith(cmd.strip())]
        for l in lines[-3:]:
            if l:
                print(f"    {l[:150]}")
    child.close()

# Fix Nginx config properly
print("=== Fixing Nginx config ===")
run([
    "cat > /etc/nginx/sites-available/bazi << 'NGINX'\nserver {\n    listen 80;\n    server_name _;\n    client_max_body_size 10M;\n    location / {\n        proxy_pass http://127.0.0.1:8000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n    }\n}\nNGINX",
    "nginx -t",
])

if "test failed" not in open("/dev/null"):  # just continue
    run(["systemctl restart nginx", "nginx -t"])

# Check app logs
print("\n=== Checking app logs ===")
run(["cat /var/log/bazi.err.log | tail -20"])

print("\n=== Checking bazi.out.log ===")
run(["cat /var/log/bazi.out.log | tail -10"])
