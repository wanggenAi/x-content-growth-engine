"""Run manually in a local terminal. Credentials never echo."""
import getpass
import os
import sys
from .settings import PRIVATE_DIR

def main():
    if not sys.stdin.isatty():
        raise SystemExit('请在自己的交互终端运行；不接受聊天中的凭证')
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    api_id = getpass.getpass('Telegram api_id（隐藏输入）: ').strip()
    api_hash = getpass.getpass('Telegram api_hash（隐藏输入）: ').strip()
    if not api_id.isdigit() or len(api_hash) != 32 or any(c not in '0123456789abcdefABCDEF' for c in api_hash):
        raise SystemExit('凭证格式无效；未保存')
    path = PRIVATE_DIR / 'credentials.env'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(f'TG_API_ID={api_id}\nTG_API_HASH={api_hash}\n')
    print('已保存到本机私密文件。接下来运行 python -m telegram_research.auth')

if __name__ == '__main__':
    main()
