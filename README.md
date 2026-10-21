# MãeSegura

Plataforma de acompanhamento da gravidez e do pós-parto para comunidades com
conectividade limitada, em português e Emakhuwa. Protótipo da Energisa para a
candidatura ao **UNICEF Femtech Ventures** (prazo: 4 de Novembro de 2026).

Licença: [MIT](LICENSE). Código aberto de ponta a ponta — servidor, base de
dados, interface e base de conhecimento.

---

## O que faz

1. **Registo mínimo.** A mulher indica a semana de gravidez. Não há campo para o
   nome: a identificação é um código curto de seis caracteres que ela guarda.
2. **Calendário de consultas** gerado segundo o modelo de 8 contactos pré-natais
   da OMS (12, 20, 26, 30, 34, 36, 38 e 40 semanas), ajustado à semana em que se
   registou.
3. **Assistente de perguntas e respostas** em português e Emakhuwa, que recupera
   conteúdo clínico validado e encaminha para a unidade sanitária quando
   reconhece um sinal de perigo.
4. **Funciona sem rede.** A base de conhecimento validada é guardada no
   telemóvel e o mesmo algoritmo de busca corre em JavaScript quando não há
   ligação.
5. **Painel público de métricas** em `/painel/` e `/api/metricas.json`, com
   dados agregados e anónimos.

## Duas decisões que explicam o resto do código

**O assistente não gera texto.** Recupera e devolve exactamente o que um
profissional de saúde escreveu e assinou, ou admite que não sabe e encaminha.
Não há modelo de linguagem na cadeia. Isto mantém o sistema inteiramente aberto
(sem backend proprietário), impede respostas inventadas sobre gravidez e permite
que tudo funcione offline. A variável `LLM_ACTIVO` existe, está desligada e
nenhuma funcionalidade depende dela.

**Nada é servido sem validação humana registada.** Um conteúdo só chega à
utilizadora se tiver `validado_por` e `validado_em` preenchidos por um clínico
em `/gestao/`. O carregador de conteúdo inicial deixa tudo por validar de
propósito. A regra é verificável em `apps/assistente/tests.py`.

## Estado da base de conhecimento

Os 23 conteúdos iniciais foram redigidos a partir das recomendações da OMS sobre
cuidados pré-natais (2016) e cuidados pós-natais. **Carecem de duas revisões
antes de qualquer uso real:**

- **Revisão clínica** por profissional de saúde, face às normas do MISAU em
  vigor. Enquanto não acontecer, a aplicação não serve nada.
- **Revisão linguística** das traduções para Emakhuwa, por falante nativo com
  formação em saúde. Os textos em Emakhuwa são rascunhos de trabalho; o campo
  `traducao_vmw_validada` só deve ser marcado depois dessa revisão.

## Correr localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py carregar_conhecimento --validar-como "Dra. Exemplo (DEMONSTRAÇÃO)"
python manage.py createsuperuser
python manage.py runserver
```

Sem `POSTGRES_DB` definido, usa SQLite — é o que permite correr os testes sem
infra-estrutura. Com Docker: `docker compose up --build`.

## Testes

```bash
python manage.py test
```

45 testes. Cobrem o cálculo da data prevista do parto, o calendário da OMS, a
regra de validação clínica, a precisão do motor de busca (incluindo perguntas
fora do domínio, que não devem devolver nada) e a ausência de dados pessoais no
painel público.

## Dados e privacidade

- O modelo `Gestante` não tem campo de nome, apelido ou documento — e há um
  teste que falha se alguém acrescentar um.
- O telefone é opcional.
- O consentimento é registado com data e versão do texto.
- A telemetria (`EventoUso`) guarda tipo de evento, idioma e distrito. Nunca o
  texto da pergunta nem qualquer identificador.
- O painel público expõe apenas contagens agregadas.

Um piloto com recolha de dados clínicos junto de grávidas exige aprovação do
Comité Nacional de Bioética para a Saúde. O que este protótipo suporta sem essa
aprovação é teste de usabilidade do produto com consentimento informado escrito.

## Estrutura

```
config/              Configuração Django
apps/core/           Idioma da interface, healthcheck, service worker
apps/acompanhamento/ Gestante, consultas, calendário da OMS, telemetria
apps/assistente/     Conteúdo clínico, validação, motor de busca
apps/painel/         Métricas públicas (HTML e JSON)
static/js/app.js     Espelho do motor de busca, para funcionar offline
deploy/              Bloco do Caddy para a VPS partilhada
```

> O algoritmo de `apps/assistente/busca.py` e o de `static/js/app.js` têm de
> permanecer idênticos. Quem alterar um tem de alterar o outro.

## Publicação

Ver [DEPLOY.md](DEPLOY.md).
