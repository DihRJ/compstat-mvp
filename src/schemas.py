"""
Schemas Pydantic - MVP 3h.

Tudo necessário em 1 arquivo:
- Áreas (CRUD com criação/exclusão)
- Ocorrências (com modus operandi)
- RELINTs (oficial, peso alto) + Denúncias (anônimo, peso baixo)
- Score com pesos diferenciados
- Recomendação de modalidade FM (a pé / moto / viatura)
- QMD (Quadro de Missão Diária)
- Snapshot de evolução 90 dias
- Feedback dos órgãos
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime, date
from uuid import uuid4


# ============================================================
# TIPOS BASE
# ============================================================

ModalidadeCrime = Literal[
    "a_pe", "motocicleta", "veiculo", "grupo_armado", "arrastao",
]

TipoOcorrencia = Literal[
    "roubo_transeunte", "roubo_celular", "roubo_coletivo", "roubo_veiculo",
    "roubo_comercio",
    "furto_transeunte", "furto_residencia", "furto_comercio",
]

OrgaoMunicipal = Literal[
    "COMLURB", "SEOP", "CET_RIO", "RIOLUZ", "SECONSERVA",
    "SMAS", "SMS", "GM_RIO", "FM",
]

ModalidadeFM = Literal["a_pe", "moto", "viatura", "mista"]

TipoFaccao = Literal["TCP", "CV", "ADA", "TCA", "milicia", "milicia_LE", "desconhecida"]

CategoriaFatorUrbano = Literal[
    "iluminacao_deficiente", "vegetacao_obstrutiva", "calcada_obstruida",
    "estacionamento_irregular", "ponto_onibus_inseguro", "psr_concentrada",
    "comercio_irregular", "esconderijo", "lixo_entulho",
    "ponto_cego_camera", "outro",
]

StatusAcao = Literal[
    "pendente", "enviada", "realizado", "nao_realizado",
    "nao_fez_sentido", "em_andamento",
]

DiaSemana = Literal["dom", "seg", "ter", "qua", "qui", "sex", "sab"]


# ============================================================
# COORDENADA
# ============================================================

class Coordenada(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    descricao: Optional[str] = None


# ============================================================
# ÁREAS (CRUD COMPLETO: CRIAR, EDITAR, EXCLUIR)
# ============================================================

class AreaPoligonoFM(BaseModel):
    poligono_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    nome_area: str
    aisp: str
    bairros: list[str]
    geometria_wkt: str
    base_fm: str
    subprefeitura: str
    dp: Optional[str] = None
    bpm: Optional[str] = None
    ativo: bool = True
    centroide: Optional[Coordenada] = None
    criado_em: datetime = Field(default_factory=datetime.now)
    atualizado_em: datetime = Field(default_factory=datetime.now)
    observacoes: Optional[str] = None


# ============================================================
# OCORRÊNCIA COM MODUS OPERANDI
# ============================================================

class Ocorrencia(BaseModel):
    """Crime registrado pela 190/DP, com modus operandi quando disponível."""
    ocorrencia_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    poligono_fm_id: str
    tipo: TipoOcorrencia
    modalidade_crime: ModalidadeCrime
    coordenada: Coordenada
    data_hora: datetime
    dia_semana: DiaSemana
    hora: int = Field(..., ge=0, le=23)
    descricao_modus: Optional[str] = Field(
        None,
        description="Modus operandi observado, se disponível",
    )


# ============================================================
# RELINT (OFICIAL - PESO ALTO NO SCORE)
# ============================================================

class RotaFuga(BaseModel):
    """Rota de fuga descrita no RELINT, usada para amplificar score."""
    descricao: str
    pontos: list[Coordenada] = Field(..., min_length=2)
    modalidade_fuga: ModalidadeCrime
    horario_predominante: Optional[str] = None


class RelintEstruturado(BaseModel):
    """
    Documento OFICIAL produzido pelo BPM ou FM.
    Tem PESO MAIOR no score por ser fonte verificada.
    """
    relint_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    poligono_fm_id: str
    autor_orgao: str = Field(..., description="ex: '14 BPM', 'Base FM Bangu'")
    data_documento: date

    # Dinâmica
    modus_operandi_principal: str
    modalidades_crime: list[ModalidadeCrime] = Field(..., min_length=1)
    tipos_ocorrencia_alvo: list[TipoOcorrencia] = Field(..., min_length=1)
    horario_pico: str
    dias_criticos: list[DiaSemana] = Field(..., min_length=1)

    # Geo crítico
    rotas_fuga: list[RotaFuga] = Field(default_factory=list)
    pontos_receptacao: list[Coordenada] = Field(default_factory=list)
    esconderijos: list[Coordenada] = Field(default_factory=list)

    # Inteligência
    orcrim_influencia: Optional[TipoFaccao] = None
    confianca: Literal["alta", "media", "baixa"] = "alta"  # default alta por ser oficial
    citacao_fonte: str = Field(..., max_length=400)


# ============================================================
# DISQUE DENÚNCIA (ANÔNIMO - PESO MENOR)
# ============================================================

class DenunciaDisque(BaseModel):
    """
    Denúncia anônima. PESO MENOR no score por ser não-verificada.
    Em volume, ainda assim gera padrões valiosos.
    """
    denuncia_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    poligono_fm_id: str
    data_recebimento: datetime
    texto: str
    local_mencionado: Optional[Coordenada] = None
    horario_mencionado: Optional[str] = None
    tema_principal: Optional[str] = None  # ex: "drogas", "receptacao", "violencia"


class PadraoDisqueDenuncia(BaseModel):
    """Padrão extraído de múltiplas denúncias."""
    padrao_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    poligono_fm_id: str
    tipo_padrao: Literal[
        "local_recorrente", "horario_concentrado", "modus_repetido",
        "suspeito_recorrente", "rota_fuga_recorrente",
    ]
    descricao: str
    n_denuncias: int = Field(..., ge=2)
    relevancia: Literal["baixa", "media", "alta", "critica"]
    citacoes: list[str] = Field(..., min_length=2)


# ============================================================
# FATOR URBANO
# ============================================================

class FatorUrbano(BaseModel):
    fator_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    poligono_fm_id: str
    categoria: CategoriaFatorUrbano
    descricao: str
    coordenada: Coordenada
    orgao_responsavel: OrgaoMunicipal
    severidade: Literal["baixa", "media", "alta", "critica"]


# ============================================================
# SCORE COM PESOS DIFERENCIADOS (RELINT > DISQUE)
# ============================================================

class ComponentesScore(BaseModel):
    """
    Detalhamento auditável do score.

    PESOS (novo MVP, do briefing + pedido Diego):
      mancha_criminal: 0.40 (ocorrências oficiais, base quantitativa)
      relint_oficial:  0.30 (RELINTs do BPM/FM, fonte oficial qualitativa)
      fator_urbano:    0.15 (mapeamento das subprefeituras)
      disque_denuncia: 0.10 (denúncias anônimas, fonte não-verificada)
      bonus_modus:     0.05 (modus operandi + rotas de fuga amplificam)

    Soma máxima: 1.00 antes do bônus faccional multiplicativo.
    """
    score_mancha: float = Field(..., ge=0, le=1)
    score_relint: float = Field(..., ge=0, le=1)
    score_fator: float = Field(..., ge=0, le=1)
    score_disque: float = Field(..., ge=0, le=1)
    score_modus_rota: float = Field(default=0.0, ge=0, le=1)

    peso_mancha: float = 0.40
    peso_relint: float = 0.30
    peso_fator: float = 0.15
    peso_disque: float = 0.10
    peso_modus: float = 0.05

    bonus_faccional: float = Field(default=1.0, ge=1.0, le=1.5)

    @property
    def score_final(self) -> float:
        base = (
            self.score_mancha * self.peso_mancha
            + self.score_relint * self.peso_relint
            + self.score_fator * self.peso_fator
            + self.score_disque * self.peso_disque
            + self.score_modus_rota * self.peso_modus
        )
        return min(base * self.bonus_faccional, 1.0)


class BingoArea(BaseModel):
    """Score consolidado por área (não por segmento, para MVP rápido)."""
    poligono_fm_id: str
    nome_area: str
    componentes: ComponentesScore
    n_camadas_ativas: int  # quantas das 4 fontes contribuem
    justificativa: str
    faccoes_envolvidas: list[TipoFaccao] = Field(default_factory=list)


# ============================================================
# RECOMENDAÇÃO DE MODALIDADE FM
# ============================================================

class RecomendacaoModalidade(BaseModel):
    """
    Sugestão de modalidade de patrulhamento baseada no:
    - Modus operandi predominante (RELINT)
    - Rotas de fuga (interceptação)
    - Tipos de crime (roubo a pé = patrulha a pé, roubo veicular = viatura)
    """
    poligono_fm_id: str
    modalidade_principal: ModalidadeFM
    modalidade_secundaria: Optional[ModalidadeFM] = None
    n_viaturas: int = Field(default=0, ge=0, le=10)
    n_motos: int = Field(default=0, ge=0, le=20)
    n_agentes_a_pe: int = Field(default=0, ge=0, le=80)
    justificativa: str
    pontos_intercepcao: list[Coordenada] = Field(
        default_factory=list,
        description="Pontos sugeridos para posicionar viaturas (rotas de fuga)",
    )
    horario_recomendado: str
    dias_recomendados: list[DiaSemana]


# ============================================================
# QMD - QUADRO DE MISSÃO DIÁRIA (NOVO)
# ============================================================

class QMD(BaseModel):
    """
    Quadro de Missão Diária: documento gerado para cada base/área da FM
    com a ordem de serviço do dia.

    Equivalente operacional do Boletim de Briefing usado pelas polícias.
    """
    qmd_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    poligono_fm_id: str
    nome_area: str
    data_referencia: date
    base_fm: str

    # Efetivo
    efetivo_alocado: int
    modalidade: ModalidadeFM
    n_viaturas: int = 0
    n_motos: int = 0
    n_agentes_a_pe: int = 0

    # Operação
    horario_cobertura: str
    dias_cobertura: list[DiaSemana]
    pontos_prioritarios: list[Coordenada] = Field(
        ...,
        description="3-5 pontos quentes para passagem obrigatória",
        min_length=1,
    )
    rotas_monitorar: list[str] = Field(
        default_factory=list,
        description="Rotas de fuga conhecidas para monitorar interceptação",
    )

    # Inteligência
    modus_operandi_atencao: str
    orcrim_atencao: Optional[TipoFaccao] = None
    foco_tipos_crime: list[TipoOcorrencia] = Field(..., min_length=1)

    # Apoio interinstitucional
    apoio_esperado: list[dict] = Field(
        default_factory=list,
        description="Ex: [{'orgao': 'COMLURB', 'acao': 'poda dia X'}]",
    )

    gerado_em: datetime = Field(default_factory=datetime.now)
    observacoes: Optional[str] = None


# ============================================================
# EVOLUÇÃO 90 DIAS
# ============================================================

class SnapshotIndicadores(BaseModel):
    """Foto dos indicadores num momento específico."""
    snapshot_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    poligono_fm_id: str
    data_referencia: date
    total_roubos: int = Field(..., ge=0)
    total_furtos: int = Field(..., ge=0)
    score_medio: float = Field(..., ge=0, le=1)
    ranking_pct: float = Field(..., ge=0, le=100)


class ComparativoEvolucao(BaseModel):
    """Comparativo entre 2 snapshots (antes vs depois da atuação FM)."""
    poligono_fm_id: str
    nome_area: str
    snapshot_antes: SnapshotIndicadores
    snapshot_depois: SnapshotIndicadores
    dias_entre: int = Field(..., ge=1)
    variacao_roubos_pct: float
    variacao_furtos_pct: float
    variacao_score_pct: float
    classificacao: Literal["melhora_significativa", "melhora_leve", "estavel", "piora_leve", "piora_significativa"]
    observacao: str


# ============================================================
# AÇÕES E FEEDBACK
# ============================================================

class AcaoRecomendada(BaseModel):
    acao_id: str = Field(default_factory=lambda: str(uuid4())[:12])
    poligono_fm_id: str
    orgao_responsavel: OrgaoMunicipal
    descricao_acao: str
    prazo_sugerido_dias: int = Field(default=7, ge=1, le=90)
    prioridade: Literal["baixa", "media", "alta", "critica"]
    contexto_origem: str
    gerada_em: datetime = Field(default_factory=datetime.now)


class FeedbackAcao(BaseModel):
    acao_id: str
    status: StatusAcao
    justificativa: Optional[str] = None
    atualizado_em: datetime = Field(default_factory=datetime.now)
    atualizado_por: str
