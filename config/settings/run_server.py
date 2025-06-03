import os
import sys
import subprocess


def run_server():
    """개발 서버 실행"""

    # 인코딩 환경 변수 설정
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['DJANGO_SETTINGS_MODULE'] = 'yakun.settings'

    # Windows에서 UTF-8 지원
    if sys.platform == 'win32':
        os.system('chcp 65001')  # UTF-8 코드페이지 설정

    # Django 개발 서버 실행
    try:
        subprocess.run([
            sys.executable, 'manage.py', 'runserver',
            '0.0.0.0:8000',  # 모든 IP에서 접근 가능
            '--settings=yakun.settings'
        ], check=True, encoding='utf-8')
    except subprocess.CalledProcessError as e:
        print(f"서버 실행 실패: {e}")
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")


if __name__ == '__main__':
    run_server()