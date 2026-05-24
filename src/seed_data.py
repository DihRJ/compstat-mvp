"""
Seed de dados realistas para 5 áreas-piloto do Rio.

Áreas escolhidas (cobrem zonas diversas):
1. Calçadão de Bangu (caso do briefing oficial)
2. Calçadão de Copacabana
3. Largo da Lapa
4. Méier (Rua Dias da Cruz)
5. Tijuca (Praça Saens Peña)

Gera 5 arquivos JSON em data/:
- areas_iniciais.json
- ocorrencias.json
- relints.json
- denuncias.json
- fatores_urbanos.json
- snapshots_90d.json (para comparativo evolutivo)

Roda com: python -m src.seed_data
"""

import json
import random
from datetime import datetime, date, timedelta
from pathlib import Path

random.seed(42)  # determinístico para reprodutibilidade do pitch


# ============================================================
# 5 ÁREAS PILOTO COM POLÍGONOS REAIS
# ============================================================

AREAS_INICIAIS = [
    {
        "poligono_id": "bangu_01",
        "nome_area": "Calcadao de Bangu",
        "aisp": "AISP 9",
        "bairros": ["Bangu"],
        "geometria_wkt": "POLYGON((-43.4685 -22.8810, -43.4670 -22.8810, -43.4670 -22.8775, -43.4685 -22.8775, -43.4685 -22.8810))",
        "base_fm": "Base FM Bangu",
        "subprefeitura": "Zona Oeste",
        "dp": "34a DP",
        "bpm": "14 BPM",
        "ativo": True,
        "centroide": {"lat": -22.8792, "lng": -43.4677},
        "criado_em": "2026-05-20T08:00:00",
        "atualizado_em": "2026-05-20T08:00:00",
        "observacoes": "Caso do briefing oficial. 70 roubos no periodo.",
    },
    {
        "poligono_id": "copa_01",
        "nome_area": "Calcadao Copacabana Posto 4",
        "aisp": "AISP 19",
        "bairros": ["Copacabana"],
        "geometria_wkt": "POLYGON((-43.1855 -22.9740, -43.1830 -22.9740, -43.1830 -22.9710, -43.1855 -22.9710, -43.1855 -22.9740))",
        "base_fm": "Base FM Copacabana",
        "subprefeitura": "Zona Sul",
        "dp": "12a DP",
        "bpm": "19 BPM",
        "ativo": True,
        "centroide": {"lat": -22.9725, "lng": -43.1842},
        "criado_em": "2026-05-20T08:00:00",
        "atualizado_em": "2026-05-20T08:00:00",
        "observacoes": "Area turistica. Picos de fim de semana e periodo do verao.",
    },
    {
        "poligono_id": "lapa_01",
        "nome_area": "Largo da Lapa",
        "aisp": "AISP 5",
        "bairros": ["Lapa", "Centro"],
        "geometria_wkt": "POLYGON((-43.1810 -22.9135, -43.1785 -22.9135, -43.1785 -22.9110, -43.1810 -22.9110, -43.1810 -22.9135))",
        "base_fm": "Base FM Centro",
        "subprefeitura": "Centro",
        "dp": "5a DP",
        "bpm": "5 BPM",
        "ativo": True,
        "centroide": {"lat": -22.9122, "lng": -43.1797},
        "criado_em": "2026-05-20T08:00:00",
        "atualizado_em": "2026-05-20T08:00:00",
        "observacoes": "Vida noturna intensa. Concentracao 22h-04h.",
    },
    {
        "poligono_id": "meier_01",
        "nome_area": "Dias da Cruz Meier",
        "aisp": "AISP 3",
        "bairros": ["Meier"],
        "geometria_wkt": "POLYGON((-43.2820 -22.9020, -43.2795 -22.9020, -43.2795 -22.8995, -43.2820 -22.8995, -43.2820 -22.9020))",
        "base_fm": "Base FM Meier",
        "subprefeitura": "Zona Norte",
        "dp": "23a DP",
        "bpm": "3 BPM",
        "ativo": True,
        "centroide": {"lat": -22.9007, "lng": -43.2807},
        "criado_em": "2026-05-20T08:00:00",
        "atualizado_em": "2026-05-20T08:00:00",
        "observacoes": "Comercio popular. Roubos motociclistas no comercio.",
    },
    {
        "poligono_id": "tijuca_01",
        "nome_area": "Praca Saens Pena",
        "aisp": "AISP 6",
        "bairros": ["Tijuca"],
        "geometria_wkt": "POLYGON((-43.2350 -22.9265, -43.2320 -22.9265, -43.2320 -22.9235, -43.2350 -22.9235, -43.2350 -22.9265))",
        "base_fm": "Base FM Tijuca",
        "subprefeitura": "Grande Tijuca",
        "dp": "19a DP",
        "bpm": "6 BPM",
        "ativo": True,
        "centroide": {"lat": -22.9250, "lng": -43.2335},
        "criado_em": "2026-05-20T08:00:00",
        "atualizado_em": "2026-05-20T08:00:00",
        "observacoes": "Polo de servicos. Saidas de metro com concentracao.",
    },
]


# ============================================================
# RELINTS OFICIAIS (1 por area, peso ALTO no score)
# ============================================================

RELINTS = [
    {
        "relint_id": "rel_bangu_01",
        "poligono_fm_id": "bangu_01",
        "autor_orgao": "14 BPM",
        "data_documento": "2026-05-15",
        "modus_operandi_principal": "Roubos a transeunte praticados a pe por grupos de 2-3 individuos, abordagem rapida no calcadao. Foco em celulares.",
        "modalidades_crime": ["a_pe"],
        "tipos_ocorrencia_alvo": ["roubo_celular", "roubo_transeunte"],
        "horario_pico": "20:00-23:00",
        "dias_criticos": ["sex", "sab"],
        "rotas_fuga": [
            {
                "descricao": "Rota A: calcadao -> Av Conego Vasconcelos -> Rua Sao Goncalo (receptacao)",
                "pontos": [
                    {"lat": -22.8792, "lng": -43.4677, "descricao": "Centro do calcadao"},
                    {"lat": -22.8780, "lng": -43.4685, "descricao": "Av Conego"},
                    {"lat": -22.8770, "lng": -43.4690, "descricao": "Rua Sao Goncalo - receptacao"},
                ],
                "modalidade_fuga": "a_pe",
                "horario_predominante": "20:00-23:00",
            }
        ],
        "pontos_receptacao": [
            {"lat": -22.8770, "lng": -43.4690, "descricao": "Comercio irregular Rua Sao Goncalo"}
        ],
        "esconderijos": [],
        "orcrim_influencia": "TCP",
        "confianca": "alta",
        "citacao_fonte": "Relatorio operacional 14 BPM maio/2026: confirmacao de 4 prisoes em flagrante na regiao com mesmo modus.",
    },
    {
        "relint_id": "rel_copa_01",
        "poligono_fm_id": "copa_01",
        "autor_orgao": "19 BPM",
        "data_documento": "2026-05-12",
        "modus_operandi_principal": "Arrastoes em grupos de 4-6 individuos, principalmente em finais de semana. Foco em turistas com celulares e correntes.",
        "modalidades_crime": ["arrastao", "a_pe"],
        "tipos_ocorrencia_alvo": ["roubo_celular", "roubo_transeunte"],
        "horario_pico": "16:00-19:00",
        "dias_criticos": ["sex", "sab", "dom"],
        "rotas_fuga": [
            {
                "descricao": "Rota B: orla -> Av Atlantica -> Rua Hilario de Gouveia -> metro Cardeal Arcoverde",
                "pontos": [
                    {"lat": -22.9725, "lng": -43.1842, "descricao": "Posto 4 orla"},
                    {"lat": -22.9710, "lng": -43.1830, "descricao": "Rua Hilario"},
                    {"lat": -22.9685, "lng": -43.1825, "descricao": "Metro Cardeal Arcoverde"},
                ],
                "modalidade_fuga": "a_pe",
                "horario_predominante": "fim de tarde",
            }
        ],
        "pontos_receptacao": [],
        "esconderijos": [],
        "orcrim_influencia": "CV",
        "confianca": "alta",
        "citacao_fonte": "Sintese semanal 19 BPM. Padrao confirmado em CFTV operacional.",
    },
    {
        "relint_id": "rel_lapa_01",
        "poligono_fm_id": "lapa_01",
        "autor_orgao": "5 BPM",
        "data_documento": "2026-05-18",
        "modus_operandi_principal": "Saidinha de bar e roubo de celular na multidao. Atuacao por individuos em pe e motociclistas dando cobertura para fuga rapida.",
        "modalidades_crime": ["a_pe", "motocicleta"],
        "tipos_ocorrencia_alvo": ["roubo_celular", "roubo_transeunte", "roubo_coletivo"],
        "horario_pico": "23:00-04:00",
        "dias_criticos": ["sex", "sab"],
        "rotas_fuga": [
            {
                "descricao": "Rota C: Lapa -> Av Mem de Sa (de moto) -> Saude (receptacao)",
                "pontos": [
                    {"lat": -22.9122, "lng": -43.1797, "descricao": "Largo da Lapa"},
                    {"lat": -22.9100, "lng": -43.1820, "descricao": "Av Mem de Sa"},
                    {"lat": -22.9050, "lng": -43.1900, "descricao": "Saude - receptacao"},
                ],
                "modalidade_fuga": "motocicleta",
                "horario_predominante": "madrugada",
            }
        ],
        "pontos_receptacao": [
            {"lat": -22.9050, "lng": -43.1900, "descricao": "Saude"}
        ],
        "esconderijos": [],
        "orcrim_influencia": "CV",
        "confianca": "alta",
        "citacao_fonte": "RELINT 5 BPM. Modus operandi confirmado por vitimas em 7 BOs.",
    },
    {
        "relint_id": "rel_meier_01",
        "poligono_fm_id": "meier_01",
        "autor_orgao": "3 BPM",
        "data_documento": "2026-05-10",
        "modus_operandi_principal": "Roubos a comercio por motociclistas armados, abordagem rapida durante movimento. Fuga em direcao a comunidades proximas.",
        "modalidades_crime": ["motocicleta", "veiculo"],
        "tipos_ocorrencia_alvo": ["roubo_comercio", "roubo_celular"],
        "horario_pico": "17:00-20:00",
        "dias_criticos": ["seg", "qui", "sex"],
        "rotas_fuga": [
            {
                "descricao": "Rota D: Dias da Cruz -> Adolfo Bergamini -> Encantado",
                "pontos": [
                    {"lat": -22.9007, "lng": -43.2807, "descricao": "Dias da Cruz comercio"},
                    {"lat": -22.9030, "lng": -43.2820, "descricao": "Adolfo Bergamini"},
                    {"lat": -22.9080, "lng": -43.2850, "descricao": "Acesso Encantado"},
                ],
                "modalidade_fuga": "motocicleta",
                "horario_predominante": "fim de expediente",
            }
        ],
        "pontos_receptacao": [],
        "esconderijos": [],
        "orcrim_influencia": "CV",
        "confianca": "alta",
        "citacao_fonte": "RELINT 3 BPM. 6 roubos a comercio com mesmo MO em 30 dias.",
    },
    {
        "relint_id": "rel_tijuca_01",
        "poligono_fm_id": "tijuca_01",
        "autor_orgao": "6 BPM",
        "data_documento": "2026-05-16",
        "modus_operandi_principal": "Roubo a transeunte na saida do metro Saens Pena. Atuacao a pe por individuos disfarcados de estudantes/trabalhadores.",
        "modalidades_crime": ["a_pe"],
        "tipos_ocorrencia_alvo": ["roubo_celular", "roubo_transeunte"],
        "horario_pico": "07:00-09:00",
        "dias_criticos": ["seg", "ter", "qua", "qui", "sex"],
        "rotas_fuga": [
            {
                "descricao": "Rota E: Praca Saens Pena -> Rua Garibaldi -> comercio (receptacao rapida)",
                "pontos": [
                    {"lat": -22.9250, "lng": -43.2335, "descricao": "Praca Saens Pena"},
                    {"lat": -22.9260, "lng": -43.2345, "descricao": "Rua Garibaldi"},
                ],
                "modalidade_fuga": "a_pe",
                "horario_predominante": "rush manha",
            }
        ],
        "pontos_receptacao": [],
        "esconderijos": [],
        "orcrim_influencia": None,
        "confianca": "media",
        "citacao_fonte": "RELINT 6 BPM. Padrao em 12 BOs concentrados em 2 semanas.",
    },
]


# ============================================================
# DENUNCIAS DISQUE (anonimas, peso BAIXO no score)
# ============================================================

TEMAS_DISQUE = ["receptacao", "drogas", "violencia", "ponto_de_uso", "moradores_indo_pra_la"]

def gerar_denuncias():
    denuncias = []
    textos_template = {
        "bangu_01": [
            "Vendendo celulares roubados no comercio da Rua Sao Goncalo proximo ao calcadao.",
            "Grupo de jovens armados parando pessoas no fim do calcadao a noite.",
            "Receptacao em loja de celular sem fachada na Av Conego Vasconcelos numero 200 aproximadamente.",
            "Movimento estranho na esquina do calcadao com Joao Sales a noite, sempre o mesmo grupo.",
            "Vi roubo de celular ontem por volta das 22h proximo ao posto de gasolina do calcadao.",
        ],
        "copa_01": [
            "Arrastao no posto 4 toda sexta a tarde, sempre mesmo modus.",
            "Vi grupo subindo Hilario com mochila cheia depois do arrastao na orla.",
            "Tem ponto de receptacao no inicio da Hilario de Gouveia esquina com Barata Ribeiro.",
            "Atencao para grupos de 5 jovens na orla, ja vi 3 arrastoes assim.",
        ],
        "lapa_01": [
            "Roubo de celular toda madrugada na escadaria, sempre tem motoqueiro de apoio.",
            "Vi dupla com moto vermelha fazendo ronda na esquina da Mem de Sa olhando vitimas.",
            "Receptacao de celular na Saude, predio antigo proximo a estacao.",
            "Saidinha de bar virou rotina, gerentes nao estao alertando os clientes.",
        ],
        "meier_01": [
            "Motoqueiros armados na Dias da Cruz roubando comercio fim de tarde.",
            "Dois assaltos em farmacia essa semana, sempre mesma dupla de moto.",
            "Vi moto preta sem placa fazendo reconhecimento perto do banco Itau.",
        ],
        "tijuca_01": [
            "Roubo na saida do metro Saens Pena cedo, todo dia da semana.",
            "Grupo fingindo ser estudante na praca, paquerando vitimas.",
            "Tem 3 cameras quebradas na praca, ja avisei a subprefeitura.",
        ],
    }

    for area in AREAS_INICIAIS:
        pid = area["poligono_id"]
        templates = textos_template.get(pid, [])
        for i, texto in enumerate(templates):
            denuncias.append({
                "denuncia_id": f"den_{pid}_{i:03d}",
                "poligono_fm_id": pid,
                "data_recebimento": (datetime.now() - timedelta(days=random.randint(1, 60))).isoformat(),
                "texto": texto,
                "local_mencionado": {
                    "lat": area["centroide"]["lat"] + random.uniform(-0.003, 0.003),
                    "lng": area["centroide"]["lng"] + random.uniform(-0.003, 0.003),
                    "descricao": None,
                },
                "horario_mencionado": random.choice(["20:00-23:00", "16:00-19:00", "07:00-09:00", "madrugada", None]),
                "tema_principal": random.choice(TEMAS_DISQUE),
            })
    return denuncias


# ============================================================
# OCORRENCIAS COM MODUS OPERANDI
# ============================================================

def gerar_ocorrencias():
    """Gera ocorrencias realistas seguindo o modus de cada area."""
    ocorrencias = []

    # Distribuicao por area (volume realista do briefing)
    distribuicao = {
        "bangu_01": 70,
        "copa_01": 85,
        "lapa_01": 55,
        "meier_01": 40,
        "tijuca_01": 30,
    }

    perfil_por_area = {
        "bangu_01": {
            "tipos": ["roubo_celular", "roubo_transeunte", "furto_transeunte"],
            "horas": list(range(20, 24)) + [0, 1],
            "dias": ["sex", "sab"],
            "modalidades": ["a_pe"],
            "modus": "Aborgadem a pe por grupo, foco em celular",
        },
        "copa_01": {
            "tipos": ["roubo_celular", "roubo_transeunte", "roubo_coletivo"],
            "horas": list(range(15, 20)),
            "dias": ["sex", "sab", "dom"],
            "modalidades": ["a_pe", "arrastao"],
            "modus": "Arrastao em grupo de 4-6",
        },
        "lapa_01": {
            "tipos": ["roubo_celular", "roubo_transeunte"],
            "horas": [22, 23, 0, 1, 2, 3],
            "dias": ["sex", "sab"],
            "modalidades": ["a_pe", "motocicleta"],
            "modus": "Saidinha de bar com apoio de moto",
        },
        "meier_01": {
            "tipos": ["roubo_comercio", "roubo_celular"],
            "horas": [17, 18, 19, 20],
            "dias": ["seg", "qui", "sex"],
            "modalidades": ["motocicleta", "veiculo"],
            "modus": "Roubo a comercio por motociclista",
        },
        "tijuca_01": {
            "tipos": ["roubo_celular", "roubo_transeunte"],
            "horas": [7, 8, 9],
            "dias": ["seg", "ter", "qua", "qui", "sex"],
            "modalidades": ["a_pe"],
            "modus": "Roubo na saida do metro",
        },
    }

    for area in AREAS_INICIAIS:
        pid = area["poligono_id"]
        n = distribuicao[pid]
        perfil = perfil_por_area[pid]

        for i in range(n):
            dia_sem = random.choice(perfil["dias"]) if random.random() < 0.8 else random.choice(["dom", "seg", "ter", "qua", "qui", "sex", "sab"])
            hora = random.choice(perfil["horas"]) if random.random() < 0.8 else random.randint(0, 23)
            data = datetime.now() - timedelta(days=random.randint(1, 60))

            ocorrencias.append({
                "ocorrencia_id": f"oco_{pid}_{i:04d}",
                "poligono_fm_id": pid,
                "tipo": random.choice(perfil["tipos"]),
                "modalidade_crime": random.choice(perfil["modalidades"]),
                "coordenada": {
                    "lat": area["centroide"]["lat"] + random.uniform(-0.0015, 0.0015),
                    "lng": area["centroide"]["lng"] + random.uniform(-0.0015, 0.0015),
                    "descricao": None,
                },
                "data_hora": data.isoformat(),
                "dia_semana": dia_sem,
                "hora": hora,
                "descricao_modus": perfil["modus"] if random.random() < 0.6 else None,
            })

    return ocorrencias


# ============================================================
# FATORES URBANOS
# ============================================================

def gerar_fatores():
    fatores_por_area = {
        "bangu_01": [
            ("iluminacao_deficiente", "Iluminacao publica em manutencao na entrada lateral", "RIOLUZ", "alta"),
            ("vegetacao_obstrutiva", "Vegetacao alta encobrindo postes", "COMLURB", "critica"),
            ("comercio_irregular", "Ambulantes apos 20h sem permissao", "SEOP", "media"),
        ],
        "copa_01": [
            ("ponto_cego_camera", "3 cameras CFTV quebradas no posto 4", "SECONSERVA", "alta"),
            ("comercio_irregular", "Quiosques fora do horario", "SEOP", "media"),
            ("psr_concentrada", "Concentracao PSR escadaria principal", "SMAS", "media"),
        ],
        "lapa_01": [
            ("lixo_entulho", "Entulho permanente nos Arcos", "COMLURB", "media"),
            ("iluminacao_deficiente", "Becos sem iluminacao", "RIOLUZ", "alta"),
            ("comercio_irregular", "Vendedores ambulantes excedendo limites", "SEOP", "alta"),
        ],
        "meier_01": [
            ("estacionamento_irregular", "Carros bloqueando visibilidade entrada", "CET_RIO", "media"),
            ("ponto_onibus_inseguro", "Ponto onibus sem cobertura proximo banco", "SECONSERVA", "alta"),
        ],
        "tijuca_01": [
            ("ponto_cego_camera", "Cameras Saens Pena com falha", "SECONSERVA", "critica"),
            ("comercio_irregular", "Ambulantes na boca metro", "SEOP", "media"),
            ("calcada_obstruida", "Bancas excedendo calcada", "SEOP", "baixa"),
        ],
    }

    fatores = []
    for area in AREAS_INICIAIS:
        pid = area["poligono_id"]
        for i, (categoria, descricao, orgao, severidade) in enumerate(fatores_por_area.get(pid, [])):
            fatores.append({
                "fator_id": f"fat_{pid}_{i:03d}",
                "poligono_fm_id": pid,
                "categoria": categoria,
                "descricao": descricao,
                "coordenada": {
                    "lat": area["centroide"]["lat"] + random.uniform(-0.001, 0.001),
                    "lng": area["centroide"]["lng"] + random.uniform(-0.001, 0.001),
                    "descricao": None,
                },
                "orgao_responsavel": orgao,
                "severidade": severidade,
            })
    return fatores


# ============================================================
# SNAPSHOTS 90 DIAS (antes e depois da atuacao FM)
# ============================================================

def gerar_snapshots_90d():
    """
    Gera 2 snapshots por area: 90 dias atras (antes) e hoje (depois).
    Mostra reducao em areas atendidas para demo do pitch.
    """
    snapshots = []
    hoje = date.today()
    ha_90d = hoje - timedelta(days=90)

    # Reducoes simuladas pos-atuacao FM (para pitch convincente)
    reducao_pos_atuacao = {
        "bangu_01": -0.38,
        "copa_01": -0.22,
        "lapa_01": -0.15,
        "meier_01": -0.30,
        "tijuca_01": 0.05,  # leve aumento, area que nao recebeu FM
    }

    base_indicadores = {
        "bangu_01": (113, 28, 0.82),
        "copa_01": (139, 35, 0.78),
        "lapa_01": (85, 18, 0.71),
        "meier_01": (62, 24, 0.65),
        "tijuca_01": (45, 12, 0.55),
    }

    for area in AREAS_INICIAIS:
        pid = area["poligono_id"]
        roubos_antes, furtos_antes, score_antes = base_indicadores[pid]
        var = reducao_pos_atuacao[pid]

        # Snapshot ANTES (90 dias atras)
        snapshots.append({
            "snapshot_id": f"snap_{pid}_antes",
            "poligono_fm_id": pid,
            "data_referencia": ha_90d.isoformat(),
            "total_roubos": roubos_antes,
            "total_furtos": furtos_antes,
            "score_medio": score_antes,
            "ranking_pct": random.uniform(60, 95),
        })

        # Snapshot DEPOIS (hoje)
        roubos_depois = int(roubos_antes * (1 + var))
        furtos_depois = int(furtos_antes * (1 + var * 0.7))
        score_depois = round(min(max(score_antes * (1 + var * 0.6), 0), 1), 3)

        snapshots.append({
            "snapshot_id": f"snap_{pid}_depois",
            "poligono_fm_id": pid,
            "data_referencia": hoje.isoformat(),
            "total_roubos": roubos_depois,
            "total_furtos": furtos_depois,
            "score_medio": score_depois,
            "ranking_pct": random.uniform(40, 85),
        })

    return snapshots


# ============================================================
# MAIN
# ============================================================

def main(data_dir: str = "data"):
    Path(data_dir).mkdir(parents=True, exist_ok=True)

    arquivos = {
        "areas_iniciais.json": AREAS_INICIAIS,
        "relints.json": RELINTS,
        "denuncias.json": gerar_denuncias(),
        "ocorrencias.json": gerar_ocorrencias(),
        "fatores_urbanos.json": gerar_fatores(),
        "snapshots_90d.json": gerar_snapshots_90d(),
    }

    for nome, dados in arquivos.items():
        caminho = Path(data_dir) / nome
        caminho.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"  ok {nome}: {len(dados)} registros")

    print(f"\nSeed completo em {data_dir}/")


if __name__ == "__main__":
    main()
