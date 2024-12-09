import os
import subprocess


def kill_process_on_ports(ports):
    for port in ports:
        try:
            result = subprocess.run(
                ["lsof", f"-i:{port}"], capture_output=True, text=True, check=True
            )
            # Parse the output to extract the PID
            for line in result.stdout.splitlines():
                if line.startswith("python"):  # Identify relevant process
                    pid = line.split()[1]  # PID is the second column
                    print(f"Killing process with PID {pid} on port {port}")
                    os.kill(int(pid), 9)  # Send SIGKILL to the process
        except subprocess.CalledProcessError:
            print(f"No process found running on port {port}")
        except Exception as e:
            print(f"Error handling port {port}: {e}")


if __name__ == "__main__":
    ports_to_check = [5001, 5002, 5003]
    kill_process_on_ports(ports_to_check)
