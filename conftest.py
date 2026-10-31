import atexit
import os
import shutil
import tempfile

# Senha conhecida para o admin criado no banco de teste (em produção ela é aleatória)
os.environ.setdefault('ADMIN_INITIAL_PASSWORD', '123456')

# Os testes de sincronização gravam histórico, último resultado e ganhadores. Para não
# alterar os arquivos versionados em data/, a suíte trabalha numa cópia temporária.
import updater  # noqa: E402

_DATA_TESTE = tempfile.mkdtemp(prefix='cds-data-')
shutil.copytree(updater.ORIGINAL_DATA_DIR, _DATA_TESTE, dirs_exist_ok=True)
updater.DATA_DIR = updater.ORIGINAL_DATA_DIR = _DATA_TESTE
atexit.register(shutil.rmtree, _DATA_TESTE, ignore_errors=True)
