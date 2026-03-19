import subprocess
import sys
import time
import os

def run_pipeline():
    scripts = [
        "modules/download_report.py",
        "modules/download_expert_report.py",
        "modules/compute_cohens_kappa.py",
        "modules/notify_results.py"
    ]

    print(f"🚀 Starting Pipeline at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    total_pipeline_start = time.time()

    for script in scripts:
        print(f"▶️ Executing: {script}")
        
        # Start timer for this specific script
        script_start = time.time()
        
        try:
            # check=True: Fail the whole script if this one returns an error
            subprocess.run([sys.executable, script], check=True)
            
            # Calculate duration
            duration = time.time() - script_start
            print(f"✅ Finished: {script} (Took: {duration:.2f} seconds)\n")
            
        except subprocess.CalledProcessError as e:
            duration = time.time() - script_start
            print(f"\n❌ ERROR: Pipeline failed at {script} after {duration:.2f}s")
            print(f"Exit Code: {e.returncode}")
            sys.exit(1)

    total_duration = time.time() - total_pipeline_start
    print("=" * 50)
    print(f"🎊 Pipeline completed successfully!")
    print(f"⏱️ Total Time: {total_duration/60:.2f} minutes")

if __name__ == "__main__":
    run_pipeline()