"""
Camada de idioma da interface.

Decisão: não usamos gettext. O conteúdo clínico é bilingue em base de dados
(campos _pt / _vmw) e as cadeias de interface vivem neste dicionário. Razões:
1. o mesmo dicionário é exportado para o service worker, dando interface
   bilingue offline sem segundo sistema de tradução;
2. evita o passo de compilação de .mo na imagem Docker;
3. Emakhuwa (ISO 639-3: vmw) não é uma localização conhecida do Django.
"""

IDIOMAS = (
    ("pt", "Português"),
    ("vmw", "Emakhuwa"),
)
IDIOMA_POR_DEFEITO = "pt"
CODIGOS = [codigo for codigo, _ in IDIOMAS]

CADEIAS = {
    "app.nome": {"pt": "MãeSegura", "vmw": "MãeSegura"},
    "app.lema": {
        "pt": "Acompanhamento da gravidez e do pós-parto",
        "vmw": "Onvaha muthiyana a nihiku na uyara",
    },
    "nav.inicio": {"pt": "Início", "vmw": "Wanipacerya"},
    "nav.assistente": {"pt": "Perguntas", "vmw": "Makoho"},
    "nav.consultas": {"pt": "Consultas", "vmw": "Sokonsulta"},
    "nav.painel": {"pt": "Dados públicos", "vmw": "Myaha ya atthu othene"},
    "idioma.mudar": {"pt": "Emakhuwa", "vmw": "Português"},

    "registo.titulo": {"pt": "Começar o acompanhamento", "vmw": "Opacerya ovahiwa"},
    "registo.explicacao": {
        "pt": "Não pedimos o seu nome. Só precisamos de saber em que semana da gravidez está, para lhe lembrar as consultas certas.",
        "vmw": "Khaninvekela nsina nanyu. Ninnaphavela otthokiherya wiira muri esumana xeeni ya onamwali, wira nimuupuxerye sokonsulta sanyu.",
    },
    "registo.semana": {"pt": "Em que semana de gravidez está?", "vmw": "Muri esumana xeeni ya onamwali?"},
    "registo.semana.ajuda": {
        "pt": "Se não souber ao certo, escreva o número de meses vezes quatro.",
        "vmw": "Akhala wiira khunsuwela, mwaalepe miyeri xa axexe.",
    },
    "registo.distrito": {"pt": "Distrito", "vmw": "Distrito"},
    "registo.unidade": {"pt": "Unidade sanitária mais próxima", "vmw": "Ekwartu ya ehaupa yookhanlya"},
    "registo.telefone": {"pt": "Telefone (opcional)", "vmw": "Ntthokiheryo (khaninlipeliwa)"},
    "registo.telefone.ajuda": {
        "pt": "Só para lembretes por SMS. Pode deixar em branco.",
        "vmw": "Paahi wira nimuupuxerye. Munrowa ohiya vathi.",
    },
    "registo.idioma": {"pt": "Idioma", "vmw": "Nttheko"},
    "registo.consentimento": {
        "pt": "Li e aceito que os meus dados sejam guardados de forma anónima para melhorar este serviço. Posso pedir a sua eliminação a qualquer momento.",
        "vmw": "Kinnakupali wiira myaha saka sihiheliwe nsina, wira ovaha ori ohapuwa. Kinnawerya ovekela wiira sihaleliwe.",
    },
    "registo.submeter": {"pt": "Começar", "vmw": "Opacerya"},
    "registo.erro.semana": {
        "pt": "Indique uma semana entre 4 e 42.",
        "vmw": "Mwaalepe esumana ya 4 mpaka 42.",
    },
    "registo.erro.consentimento": {
        "pt": "É preciso aceitar para continuar.",
        "vmw": "Ohaana okupali wira nivirikane.",
    },

    "inicio.saudacao": {"pt": "O seu acompanhamento", "vmw": "Ovahiwa wanyu"},
    "inicio.semana": {"pt": "Semana de gravidez", "vmw": "Esumana ya onamwali"},
    "inicio.proxima": {"pt": "Próxima consulta", "vmw": "Ekonsulta enatthara"},
    "inicio.parto": {"pt": "Data prevista do parto", "vmw": "Nihiku na uyara"},
    "inicio.codigo": {"pt": "O seu código", "vmw": "Ekodigo anyu"},
    "inicio.codigo.ajuda": {
        "pt": "Guarde este código. É com ele que volta a entrar, sem senha e sem nome.",
        "vmw": "Mwaakihe ekodigo ela. Ti yeyo enovolowa nayo.",
    },
    "inicio.faltam": {"pt": "semanas para o parto", "vmw": "isumana wira uyare"},
    "inicio.chegou": {"pt": "Está na altura do parto", "vmw": "Okathi wa uyara woophiya"},
    "inicio.hoje": {"pt": "é hoje", "vmw": "ti olelo"},
    "inicio.daqui": {"pt": "daqui a", "vmw": "muhina mahiku"},
    "inicio.de": {"pt": "de", "vmw": "a"},
    "inicio.dias": {"pt": "dias", "vmw": "mahiku"},
    "inicio.perguntar": {"pt": "Fazer uma pergunta", "vmw": "Opaka nkoho"},
    "inicio.sem.consultas": {"pt": "Sem consultas marcadas.", "vmw": "Khavo sokonsulta."},
    "inicio.realizada": {"pt": "Realizada", "vmw": "Yaakhwaniheriwa"},
    "inicio.agendada": {"pt": "Marcada", "vmw": "Yoolempwa"},
    "inicio.em.atraso": {"pt": "Em atraso", "vmw": "Yoocelela"},

    "entrar.titulo": {"pt": "Entrar com o seu código", "vmw": "Ovolowa ni ekodigo anyu"},
    "entrar.codigo": {"pt": "Código", "vmw": "Ekodigo"},
    "entrar.submeter": {"pt": "Entrar", "vmw": "Ovolowa"},
    "entrar.erro": {"pt": "Código não encontrado.", "vmw": "Ekodigo khephwanyiwe."},
    "entrar.ou": {"pt": "Já tem um código?", "vmw": "Mukhalana ekodigo?"},

    "assistente.titulo": {"pt": "Pergunte sobre a sua gravidez", "vmw": "Mukohe sa onamwali wanyu"},
    "assistente.ajuda": {
        "pt": "Escreva a sua dúvida por palavras simples. Respondemos com informação revista por profissionais de saúde.",
        "vmw": "Mwaalepe nkoho nanyu ni masu oorereela. Ninnaakhula ni myaha soolikaniheriwa ni anamalapa a ehaupa.",
    },
    "assistente.campo": {"pt": "A sua pergunta", "vmw": "Nkoho nanyu"},
    "assistente.submeter": {"pt": "Perguntar", "vmw": "Okoha"},
    "assistente.sem.resposta": {
        "pt": "Ainda não temos uma resposta revista para esta pergunta. Procure a unidade sanitária mais próxima e fale com um profissional de saúde.",
        "vmw": "Khaninnakhalana wakhula woolikaniheriwa wa nkoho nla. Mwaaye ekwartu ya ehaupa, mulavuleke ni namalapa a ehaupa.",
    },
    "assistente.fonte": {"pt": "Fonte", "vmw": "Nipuro na myaha"},
    "assistente.validado": {"pt": "Revisto por", "vmw": "Woolikaniheriwa ni"},
    "assistente.offline": {
        "pt": "Sem ligação. A responder a partir do conteúdo guardado no telemóvel.",
        "vmw": "Khuvo enterneti. Ninnaakhula ni myaha sookhaliherye vatelemovelini.",
    },
    "assistente.exemplos": {"pt": "Perguntas frequentes", "vmw": "Makoho oopakiwa vancipale"},

    "alerta.urgente": {"pt": "Procure uma unidade sanitária agora", "vmw": "Mwaaye ekwartu ya ehaupa vano"},
    "alerta.urgente.texto": {
        "pt": "O que descreveu é um sinal de perigo. Não espere pela próxima consulta.",
        "vmw": "Ele mulonceiye ti nittittimiho. Muhiwehererye ekonsulta enatthara.",
    },
    "alerta.atencao": {"pt": "Fale com o agente de saúde", "vmw": "Mulavuleke ni namalapa a ehaupa"},

    "aviso.nao.diagnostico": {
        "pt": "Este serviço dá informação de saúde revista por profissionais. Não faz diagnósticos nem substitui a consulta.",
        "vmw": "Erelatorio ela ennavaha myaha sa ehaupa. Khennilipiherya eretta, khenniholiha ekonsulta.",
    },

    "painel.titulo": {"pt": "Dados do piloto em tempo real", "vmw": "Myaha sa opiloto"},
    "painel.explicacao": {
        "pt": "Dados agregados e anónimos do piloto em curso. Nenhum dado pessoal é publicado. Actualizado a cada carregamento.",
        "vmw": "Myaha sothene ohina masina a atthu. Khavo myaha sa mutthu mmosa.",
    },
    "painel.gestantes": {"pt": "Mulheres em acompanhamento", "vmw": "Athiyana onvahiwa"},
    "painel.perguntas": {"pt": "Perguntas feitas", "vmw": "Makoho oopakiwa"},
    "painel.taxa": {"pt": "Perguntas com resposta revista", "vmw": "Makoho oowakhuliwa"},
    "painel.alertas": {"pt": "Encaminhamentos por sinal de perigo", "vmw": "Oorumeliwa o ekwartu ya ehaupa"},
    "painel.consultas": {"pt": "Consultas marcadas", "vmw": "Sokonsulta soolempwa"},
    "painel.conhecimento": {"pt": "Conteúdos validados por clínico", "vmw": "Myaha soolikaniheriwa"},
    "painel.idiomas": {"pt": "Utilização por idioma", "vmw": "Mitthekoni"},
    "painel.json": {"pt": "Dados abertos (JSON)", "vmw": "Myaha soohukhuliwa (JSON)"},
    "painel.codigo": {"pt": "Código-fonte", "vmw": "Ekodigo ya erelatorio"},
}


def traduzir(chave, idioma=IDIOMA_POR_DEFEITO):
    entrada = CADEIAS.get(chave)
    if entrada is None:
        return chave
    return entrada.get(idioma) or entrada[IDIOMA_POR_DEFEITO]


def dicionario(idioma=IDIOMA_POR_DEFEITO):
    """Dicionário plano para o service worker."""
    return {chave: traduzir(chave, idioma) for chave in CADEIAS}
