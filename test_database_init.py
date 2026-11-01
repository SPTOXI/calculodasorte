"""init_db precisa aguentar várias instâncias serverless subindo ao mesmo tempo."""

from concurrent.futures import ThreadPoolExecutor

import database


def test_init_db_concorrente_nao_gera_deadlock():
    def iniciar(_):
        database.init_db()
        return True

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(pool.map(iniciar, range(16)))
