#!/usr/bin/env python3
"""
测试调试脚本
运行单个测试文件并查看详细错误信息
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add apps to Python path like manage.py does
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
apps_dir = os.path.join(BASE_DIR, "apps")
sys.path.insert(0, apps_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meeting_platform.settings.test')

# Setup Django
django.setup()

def run_test_file(file_path):
    """运行单个测试文件"""
    # Remove the meeting_platform prefix
    relative_path = file_path.replace('meeting_platform/', '')

    # Get the test runner
    TestRunner = get_runner(settings)

    # Run specific test file
    test_runner = TestRunner()
    failures = test_runner.run_tests([relative_path])

    return failures

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_tests.py <test_file_path>")
        print("Example: python debug_tests.py meeting/test_meeting.py")
        sys.exit(1)

    test_file = sys.argv[1]
    failures = run_test_file(test_file)
    sys.exit(bool(failures))