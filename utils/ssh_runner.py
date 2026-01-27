
import os
import pty
import select
import time
import subprocess
import sys

# Config
HOST = "192.168.31.150"
USER = "shumeipai" # Updated from pi
PASS = "12345678" # Assuming same password, update if known diff
CMD = "cd jarvis && python3 hybrid_jarvis.py" # Updated path to ~/jarvis

def run_ssh():
    # SSH command with pseudo-tty allocation (-t)
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{USER}@{HOST}", "-t", CMD]
    
    print(f"🚀 Connecting to {USER}@{HOST}...")
    
    # Fork process with pty
    pid, fd = pty.fork()
    
    if pid == 0:
        # Child process: Exec ssh
        try:
            os.execvp(ssh_cmd[0], ssh_cmd)
        except Exception as e:
            sys.stderr.write(f"Error starting ssh: {e}\n")
            sys.exit(1)
            
    else:
        # Parent process: Handle IO
        password_sent = False
        buffer = b""
        
        try:
            while True:
                # Check if data available to read
                r, w, x = select.select([fd], [], [], 0.1)
                
                if fd in r:
                    try:
                        data = os.read(fd, 1024)
                        if not data:
                            break
                        
                        # Print output live
                        sys.stdout.buffer.write(data)
                        sys.stdout.buffer.flush()
                        
                        buffer += data
                        
                        # Handle Password Prompt
                        if not password_sent and (b"password:" in buffer.lower() or b"password" in buffer.lower()):
                            print("🔑 Sending password...")
                            os.write(fd, f"{PASS}\n".encode())
                            password_sent = True
                            buffer = b"" # Reset buffer to avoid re-triggering (though simple check usually ok)
                            
                    except OSError:
                        break
        except Exception as e:
            print(f"Monitor error: {e}")
        finally:
            # Clean exit
            os.close(fd)
            try:
                os.waitpid(pid, 0)
            except:
                pass
            print(f"\n🔌 Disconnected from {HOST}")

if __name__ == "__main__":
    run_ssh()
