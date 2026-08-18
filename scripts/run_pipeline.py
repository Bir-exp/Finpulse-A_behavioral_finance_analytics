from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent


PIPELINE_SCRIPTS = [
    "generate_finpulse_dataset.py",
    "build_features.py",
    "signal_engine.py",
    "score_engine.py",
    "recommendation_engine.py",
    "segmentation_engine.py",
]


def run_script(script_name):
    script_path = (
        PROJECT_ROOT
        / "scripts"
        / script_name
    )

    print("\n" + "=" * 60)
    print(f"Running: {script_name}")
    print("=" * 60)

    subprocess.run(
        [
            sys.executable,
            str(script_path)
        ],
        check=True,
        cwd=PROJECT_ROOT
    )


def main():

    print("\nStarting FinPulse pipeline...\n")

    try:

        for script in PIPELINE_SCRIPTS:
            run_script(script)

    except subprocess.CalledProcessError as error:

        print("\nPipeline failed.")

        print(
            f"Failed script returned "
            f"exit code: {error.returncode}"
        )

        raise SystemExit(1)

    print("\n" + "=" * 60)
    print("FinPulse pipeline completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()