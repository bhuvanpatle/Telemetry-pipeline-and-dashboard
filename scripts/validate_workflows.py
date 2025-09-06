#!/usr/bin/env python3
"""
Local validation script for CI/CD workflows.
This script simulates workflow steps locally for testing.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description, cwd=None):
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Error: {e.stderr}")
        return False


def validate_workflows():
    """Validate workflow files and simulate CI steps"""
    print("🚀 LOCAL CI/CD VALIDATION")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path(".github/workflows").exists():
        print("❌ Run this script from the project root directory")
        return False

    success_count = 0
    total_tests = 0

    # 1. Validate YAML syntax
    print("\n📄 YAML Syntax Validation")
    print("-" * 30)
    workflow_files = [
        ".github/workflows/ci.yml",
        ".github/workflows/deploy_frontend.yml",
        ".github/workflows/release.yml"
    ]

    for workflow in workflow_files:
        total_tests += 1
        try:
            import yaml
            with open(workflow, 'r') as f:
                yaml.safe_load(f)
            print(f"✅ {workflow} - Valid YAML")
            success_count += 1
        except Exception as e:
            print(f"❌ {workflow} - Invalid YAML: {e}")

    # 2. Python backend validation
    print("\n🐍 Python Backend Validation")
    print("-" * 30)

    # Check requirements.txt
    total_tests += 1
    if Path("requirements.txt").exists():
        print("✅ requirements.txt found")
        success_count += 1
    else:
        print("❌ requirements.txt not found")

    # Run flake8 if available
    total_tests += 1
    if run_command("python -m flake8 --version", "Check flake8 availability"):
        if run_command(
            "python -m flake8 . --count --select=E9,F63,F7,F82 --exclude=venv,env,.venv,.env,node_modules",
            "Python syntax check"
        ):
            success_count += 1

    # Run pytest if available
    total_tests += 1
    if run_command("python -m pytest --version", "Check pytest availability"):
        if run_command("python -m pytest FAT_tests/ --collect-only", "Test discovery"):
            success_count += 1

    # 3. Frontend validation
    print("\n🟢 Frontend Validation")
    print("-" * 30)

    # Check package.json
    total_tests += 1
    frontend_package = Path("frontend/package.json")
    if frontend_package.exists():
        print("✅ frontend/package.json found")
        success_count += 1
    else:
        print("❌ frontend/package.json not found")

    # Check Node.js availability
    total_tests += 1
    if run_command("node --version", "Check Node.js availability"):
        success_count += 1

    # Check npm scripts
    total_tests += 1
    if frontend_package.exists():
        if run_command("npm run build --if-present", "Frontend build check", cwd="frontend"):
            success_count += 1

    # 4. Docker validation
    print("\n🐳 Docker Validation")
    print("-" * 30)

    total_tests += 1
    if run_command("docker --version", "Check Docker availability"):
        success_count += 1

    total_tests += 1
    if Path("docker-compose.yml").exists():
        if run_command("docker-compose config", "Docker Compose validation"):
            success_count += 1

    # 5. Documentation validation
    print("\n📚 Documentation Validation")
    print("-" * 30)

    docs_files = [
        "README.md",
        "docs/ci_cd.md",
        ".github/workflows/ci.yml",
        ".github/workflows/deploy_frontend.yml",
        ".github/workflows/release.yml"
    ]

    for doc in docs_files:
        total_tests += 1
        if Path(doc).exists():
            print(f"✅ {doc} exists")
            success_count += 1
        else:
            print(f"❌ {doc} missing")

    # Summary
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")

    if success_count == total_tests:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("Your CI/CD workflows are ready for deployment!")
        return True
    else:
        print(f"\n⚠️ {total_tests - success_count} validations failed.")
        print("Please fix the issues before deploying workflows.")
        return False


def show_next_steps():
    """Show next steps for workflow deployment"""
    print("\n🚀 NEXT STEPS")
    print("=" * 20)
    print("1. Commit the workflow files:")
    print("   git add .github/workflows/ docs/")
    print("   git commit -m 'Add comprehensive CI/CD workflows'")
    print("")
    print("2. Push to trigger CI:")
    print("   git push origin main")
    print("")
    print("3. Manual frontend deployment:")
    print("   gh workflow run deploy_frontend.yml")
    print("")
    print("4. Create a release:")
    print("   git tag v1.0.0")
    print("   git push origin v1.0.0")
    print("")
    print("5. Monitor workflows:")
    print("   https://github.com/bhuvanpatle/Telemetry-pipeline-and-dashboard/actions")


if __name__ == "__main__":
    try:
        success = validate_workflows()
        show_next_steps()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
