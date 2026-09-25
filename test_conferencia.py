"""Regras de premiação por loteria na conferência automática."""

import unittest
from unittest.mock import patch

import conferencia


class TestConferenciaPorLoteria(unittest.TestCase):

    def test_dupla_sena_confere_os_dois_sorteios(self):
        s1, s2 = [1, 2, 3, 4, 5, 6], [10, 20, 30, 40, 45, 50]
        jogos = [[1, 2, 3, 30, 40, 45],   # terno no 1º e terno no 2º: dois prêmios
                 [10, 20, 30, 40, 7, 8],  # só a quadra do 2º sorteio
                 [7, 8, 9, 11, 12, 13]]   # nada
        res, premios = conferencia.conferir_jogos('dupla_sena', jogos, s1, s2)
        self.assertIn('1º sorteio', res[0]['rotulo_premio'])
        self.assertIn('2º sorteio', res[0]['rotulo_premio'])
        self.assertIn('2º sorteio', res[1]['rotulo_premio'])
        self.assertIsNone(res[2]['rotulo_premio'])
        self.assertEqual(sum(premios.values()), 3)

    def test_mais_milionaria_faixas_com_trevos(self):
        sorteio, trevos = [1, 2, 3, 4, 5, 6], [1, 2]
        jogos = [[1, 2, 7, 8, 9, 10],   # 2 + 2 trevos: prêmio
                 [1, 2, 7, 8, 9, 10],   # 2 + 1 trevo: prêmio
                 [1, 2, 7, 8, 9, 10],   # 2 + 0 trevo: sem prêmio
                 [1, 2, 3, 8, 9, 10]]   # 3 + 0 trevo: prêmio
        trevos_jogos = [[1, 2], [1, 5], [5, 6], [5, 6]]
        res, _ = conferencia.conferir_jogos('mais_milionaria', jogos, sorteio, None, trevos, trevos_jogos)
        self.assertEqual(res[0]['rotulo_premio'], '2 + 2 trevo(s) 🎯')
        self.assertEqual(res[1]['rotulo_premio'], '2 + 1 trevo(s) 🎯')
        self.assertIsNone(res[2]['rotulo_premio'])
        self.assertEqual(res[3]['rotulo_premio'], '3 + 0 trevo(s) 🎯')

    def test_mais_milionaria_sem_trevos_do_jogo(self):
        res, _ = conferencia.conferir_jogos('mais_milionaria', [[1, 2, 3, 9, 10, 11], [1, 2, 9, 10, 11, 12]],
                                            [1, 2, 3, 4, 5, 6], None, [1, 2], None)
        self.assertIn('confira os trevos', res[0]['rotulo_premio'])
        self.assertIsNone(res[1]['rotulo_premio'])

    def test_time_do_coracao_e_mes_da_sorte(self):
        # Timemania: nome da Caixa vem com espaços extras; comparação ignora espaços e maiúsculas
        res, premios = conferencia.conferir_jogos('timemania', [[1] * 10, [2] * 10], [50, 51, 52, 53, 54, 55, 56],
                                                  complemento_sorteio='VOLTA REDONDA    /RJ',
                                                  complementos_jogos=['Volta Redonda/RJ', 'FLAMENGO/RJ'])
        self.assertEqual(res[0]['rotulo_premio'], '⚽ Time do Coração')
        self.assertIsNone(res[1]['rotulo_premio'])
        self.assertEqual(premios, {'⚽ Time do Coração': 1})
        # Dia de Sorte: mês + dezenas somam dois prêmios
        res, premios = conferencia.conferir_jogos('dia_de_sorte', [[1, 2, 3, 4, 20, 21, 22]], [1, 2, 3, 4, 5, 6, 7],
                                                  complemento_sorteio='Setembro', complementos_jogos=['setembro'])
        self.assertEqual(res[0]['rotulo_premio'], '4 Acertos + 📅 Mês da Sorte')
        self.assertEqual(sum(premios.values()), 2)

    def test_mais_milionaria_com_mais_trevos(self):
        # 6 trevos marcados: sempre acerta os 2 sorteados
        res, _ = conferencia.conferir_jogos('mais_milionaria', [[1, 2, 7, 8, 9, 10, 11, 12]], [1, 2, 3, 4, 5, 6],
                                            None, [3, 5], [[1, 2, 3, 4, 5, 6]])
        self.assertEqual(res[0]['trevos_acertados'], 2)
        self.assertEqual(res[0]['rotulo_premio'], '2 + 2 trevo(s) 🎯')

    def test_super_sete_por_coluna(self):
        res, _ = conferencia.conferir_jogos('super_sete', [[1, 2, 3, 9, 9, 9, 9]], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(res[0]['acertos_posicoes'], [0, 1, 2])
        self.assertEqual(res[0]['rotulo_premio'], '3 Acertos ⭐')
        # mesmo dígito em outra coluna não conta
        res, _ = conferencia.conferir_jogos('super_sete', [[7, 6, 5, 4, 3, 2, 1]], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(res[0]['qtd_acertos'], 1)

    def test_faixas_das_demais_loterias(self):
        casos = {
            'mega_sena': (3, None, 4, 'Quadra'),
            'quina': (1, None, 2, 'Duque'),
            'lotofacil': (10, None, 11, '11 Acertos'),
            'dia_de_sorte': (3, None, 4, '4 Acertos'),
            'timemania': (2, None, 3, '3 Acertos'),
        }
        for loteria, (sem, _, com, rotulo) in casos.items():
            self.assertIsNone(conferencia.rotulo_premio(loteria, sem), loteria)
            self.assertIn(rotulo, conferencia.rotulo_premio(loteria, com), loteria)
        self.assertIn('0 Acertos', conferencia.rotulo_premio('lotomania', 0))
        self.assertIsNone(conferencia.rotulo_premio('lotomania', 14))
        self.assertIn('15 Acertos', conferencia.rotulo_premio('lotomania', 15))

    def test_sorteio_usa_o_numero_real_do_concurso(self):
        """O concurso conferido é o pedido, mesmo com falhas no histórico local."""
        dados = {'numero': 3000, 'dataApuracao': '10/09/2026', 'listaDezenas': ['01', '02', '03', '04', '05', '06'],
                 'listaDezenasSegundoSorteio': ['10', '20', '30', '40', '45', '50']}
        with patch('conferencia.updater.carregar_meta', return_value={'ultimo_concurso': 3011}), \
                patch('conferencia.updater.carregar_ultimo_resultado_local', return_value={'numero': 3011}), \
                patch('conferencia.updater.consultar_caixa', return_value=dados) as consulta:
            conferencia._CONCURSOS_CACHE.clear()
            s = conferencia.sorteio_do_concurso('dupla_sena', 3000)
        consulta.assert_called_once()
        self.assertEqual(consulta.call_args.kwargs['concurso'], 3000)
        self.assertEqual(s['dezenas'], [1, 2, 3, 4, 5, 6])
        self.assertEqual(s['segundo_sorteio'], [10, 20, 30, 40, 45, 50])

        with patch('conferencia.updater.carregar_meta', return_value={'ultimo_concurso': 3011}), \
                patch('conferencia.updater.carregar_ultimo_resultado_local', return_value=None), \
                patch('conferencia.updater.consultar_caixa', return_value=None):
            conferencia._CONCURSOS_CACHE.clear()
            self.assertEqual(conferencia.sorteio_do_concurso('dupla_sena', 2999)['status'], 'indisponivel')


if __name__ == '__main__':
    unittest.main()
