#!/usr/bin/env python3
"""
Pipeline Health Check Script
Verifies data integrity and pipeline status for the Fantasy Football Dashboard.

This script checks:
1. Required JSON files exist and are recent
2. Data structure validity (no malformed JSON)
3. Week detection config is present
4. Python dependencies installed
5. Frontend build readiness

Run this before deploying or after returning to the project.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class HealthCheck:
    """Health check orchestrator"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.frontend_public = self.project_root / "dashboard" / "frontend" / "public"
        self.pipeline_config = self.project_root / "pipeline" / "config"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
    
    def check_file_exists(self, filepath: Path, description: str, max_age_days: int = 7) -> bool:
        """Check if file exists and is reasonably recent"""
        if not filepath.exists():
            self.errors.append(f"{description} not found: {filepath}")
            return False
        
        # Check file age
        file_age = datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)
        if file_age > timedelta(days=max_age_days):
            self.warnings.append(
                f"{description} is {file_age.days} days old (threshold: {max_age_days} days)"
            )
        
        self.passed.append(f"{description} exists")
        return True
    
    def check_json_valid(self, filepath: Path, description: str) -> bool:
        """Validate JSON structure"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Check if empty
            if not data:
                self.warnings.append(f"{description} is empty")
                return False
            
            self.passed.append(f"{description} is valid JSON")
            return True
        except json.JSONDecodeError as e:
            self.errors.append(f"{description} has invalid JSON: {e}")
            return False
        except Exception as e:
            self.errors.append(f"{description} error: {e}")
            return False
    
    def check_week_config(self) -> bool:
        """Verify week detection config"""
        week_config = self.pipeline_config / "current_week.json"
        
        if not self.check_file_exists(week_config, "Week config", max_age_days=7):
            self.errors.append(
                "Run: python3 pipeline/scripts/detect_current_week.py"
            )
            return False
        
        try:
            with open(week_config, 'r') as f:
                config = json.load(f)
            
            if 'current_week' not in config:
                self.errors.append("Week config missing 'current_week' field")
                return False
            
            week = config['current_week']
            if not (1 <= week <= 18):
                self.warnings.append(f"Unusual week number: {week}")
            
            self.passed.append(f"Week config valid: Week {week}")
            return True
        except Exception as e:
            self.errors.append(f"Week config error: {e}")
            return False
    
    def check_dashboard_data(self) -> bool:
        """Check all required dashboard JSON files"""
        required_files = [
            ("api-trades.json", "Trade data"),
            ("api-teams.json", "Team data"),
            ("api-standings.json", "Standings data"),
            ("waiver-wire-page.json", "Waiver wire data"),
            ("api-stats-summary.json", "Stats summary"),
        ]
        
        all_good = True
        for filename, description in required_files:
            filepath = self.frontend_public / filename
            
            if not self.check_file_exists(filepath, description, max_age_days=7):
                all_good = False
                continue
            
            if not self.check_json_valid(filepath, description):
                all_good = False
        
        return all_good
    
    def check_python_dependencies(self) -> bool:
        """Verify Python dependencies are installed"""
        required_modules = ['pandas', 'requests', 'yaml']
        missing = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)
        
        if missing:
            self.errors.append(
                f"Missing Python dependencies: {', '.join(missing)}\n"
                f"Run: pip install -r pipeline/requirements.txt"
            )
            return False
        
        self.passed.append("Python dependencies installed")
        return True
    
    def check_frontend_build(self) -> bool:
        """Check frontend is buildable"""
        node_modules = self.project_root / "dashboard" / "frontend" / "node_modules"
        package_json = self.project_root / "dashboard" / "frontend" / "package.json"
        
        if not package_json.exists():
            self.errors.append("Frontend package.json not found")
            return False
        
        if not node_modules.exists():
            self.warnings.append(
                "Frontend dependencies not installed\n"
                "Run: cd dashboard/frontend && npm install"
            )
            return False
        
        self.passed.append("Frontend dependencies installed")
        return True
    
    def print_results(self):
        """Print health check results with color coding"""
        print(f"\n{BOLD}{'=' * 60}{RESET}")
        print(f"{BOLD}Fantasy Football Dashboard Health Check{RESET}")
        print(f"{BOLD}{'=' * 60}{RESET}\n")
        
        # Print passed checks
        if self.passed:
            print(f"{GREEN}{BOLD}✓ Passed Checks ({len(self.passed)}):{RESET}")
            for msg in self.passed:
                print(f"  {GREEN}✓{RESET} {msg}")
            print()
        
        # Print warnings
        if self.warnings:
            print(f"{YELLOW}{BOLD}⚠ Warnings ({len(self.warnings)}):{RESET}")
            for msg in self.warnings:
                print(f"  {YELLOW}⚠{RESET} {msg}")
            print()
        
        # Print errors
        if self.errors:
            print(f"{RED}{BOLD}✗ Errors ({len(self.errors)}):{RESET}")
            for msg in self.errors:
                print(f"  {RED}✗{RESET} {msg}")
            print()
        
        # Print summary
        print(f"{BOLD}{'=' * 60}{RESET}")
        total_checks = len(self.passed) + len(self.warnings) + len(self.errors)
        
        if not self.errors and not self.warnings:
            print(f"{GREEN}{BOLD}✓ All checks passed! ({total_checks}/{total_checks}){RESET}")
            print(f"{GREEN}Dashboard is healthy and ready to deploy.{RESET}")
            return 0
        elif not self.errors:
            print(f"{YELLOW}{BOLD}⚠ Health check passed with warnings{RESET}")
            print(f"{YELLOW}Dashboard functional but has non-critical issues.{RESET}")
            return 0
        else:
            print(f"{RED}{BOLD}✗ Health check failed{RESET}")
            print(f"{RED}Fix errors above before deploying.{RESET}")
            return 1
    
    def run(self) -> int:
        """Run all health checks"""
        print(f"{BLUE}Running health checks...{RESET}\n")
        
        # Run all checks
        self.check_week_config()
        self.check_dashboard_data()
        self.check_python_dependencies()
        self.check_frontend_build()
        
        # Print results and return exit code
        return self.print_results()


def main():
    """Main entry point"""
    checker = HealthCheck()
    exit_code = checker.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()