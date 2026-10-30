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
   reconhece um sinal de perigo. Desde a v0.6.0, a procura assenta a grafia do
   Emakhuwa e usa um léxico para ligar a pergunta ao conteúdo — ver abaixo.
4. **Funciona sem rede.** A base de conhecimento validada é guardada no
   telemóvel e o mesmo algoritmo de busca corre em JavaScript quando não há
   ligação.
5. **Painel público de métricas** em `/painel/` e `/api/metricas.json`, com
   dados agregados e anónimos.
6. **Painel de gestão próprio** em `/gestao/`, com três perfis separados.
7. **Protecção anti-robô** nos quatro pontos de entrada públicos: campo-armadilha,
   carimbo de tempo assinado, limite por endereço IP, bloqueio de senhas e
   Cloudflare Turnstile opcional.

## Duas decisões que explicam o resto do código

**O assistente não gera texto.** Recupera e devolve exactamente o que um
profissional de saúde escreveu e assinou, ou admite que não sabe e encaminha.
Não há modelo de linguagem na cadeia. Isto mantém o sistema inteiramente aberto
(sem backend proprietário), impede respostas inventadas sobre gravidez e permite
que tudo funcione offline. A variável `LLM_ACTIVO` existe, está desligada e
nenhuma funcionalidade depende dela.

**Nada é servido sem validação humana registada.** Um conteúdo só chega à
utilizadora se tiver `validado_por` e `validado_em` preenchidos por um clínico
no painel de gestão. O carregador de conteúdo inicial deixa tudo por validar de
propósito. A regra é verificável em `apps/assistente/tests.py`.

## Quem faz o quê: três perfis, não três níveis

| Perfil | Vê e faz | Não pode |
|---|---|---|
| **Clínico** | Revê, edita e **assina** o conteúdo clínico; revê traduções | Gerir consultas, unidades ou contas |
| **Gestor** | Indicadores, consultas, gestantes, unidades sanitárias, exportação | **Validar ou alterar conteúdo clínico** |
| **Superuser** | Tudo, mais criação de contas e Django admin em `/sistema/` | — |

A linha que importa é a do meio. O gestor coordena o projecto, mas não assina
conteúdo clínico, por mais chefe que seja — a assinatura que a grávida vê tem de
ser de quem tem competência para a dar. É isso que torna defensável, perante o
UNICEF, a afirmação de que nenhum conteúdo clínico chega à utilizadora sem
revisão profissional. Há testes em `apps/gestao/tests.py` que falham se alguém
abrir essa porta.

O Django admin **não** é o painel de trabalho: vive em `/sistema/`, é só para
manutenção técnica, e o trabalho do dia-a-dia faz-se em `/gestao/`.

## Estado da base de conhecimento

Os 23 conteúdos iniciais foram redigidos a partir das recomendações da OMS sobre
cuidados pré-natais (2016) e cuidados pós-natais. **Carecem de duas revisões
antes de qualquer uso real:**

- **Revisão clínica** por profissional de saúde, face às normas do MISAU em
  vigor. Enquanto não acontecer, a aplicação não serve nada.
- **Revisão linguística** das traduções para Emakhuwa, por falante nativo com
  formação em saúde. Os textos em Emakhuwa são rascunhos de trabalho; o campo
  `traducao_vmw_validada` só deve ser marcado depois dessa revisão.

## O léxico do Emakhuwa (v0.6.0, alargado na v0.7.0)

O assistente usa o léxico do **Tradutor e Dicionário Emakhuwa** em
`apps/assistente/dados/lexico_vmw.json` — 307 entradas, cada uma com a
variante e o documento de onde veio. Variante de referência: **Emakhuwa
Central (`vmw`)**, a de Nampula. Base normativa: Ngunga & Faquir (2014),
*Padronização da Ortografia de Línguas Moçambicanas* (CELM/UEM); gramática de
Kröger (2009); *Vocabulário de Emakhuwa Central* (SIL, 2010). Quando duas
grafias caem na mesma chave, fica a forma Central.

Faz duas coisas, e só duas.

**Assenta a grafia.** O Emakhuwa não se escreve de uma só maneira. «okhuma
maasi» e «okuma masi» são a mesma coisa para quem as diz, e eram perguntas
diferentes para o motor de busca. Agora os dois lados da comparação passam pela
mesma normalização — aspiradas, vogais longas, `w`/`y` — e a variação deixa de
esconder a resposta. Isto vale peso inteiro: não é uma aproximação, é a mesma
palavra.

**Liga a pergunta ao conteúdo em português.** Quem escreve «muru ereca» chega
ao conteúdo sobre dor de cabeça e doença, ainda que as palavras-chave estejam
só em português. A página diz-lhe como foi entendida: *«muru» = cabeça*.

**O que o léxico nunca faz:** escrever, traduzir ou alterar uma resposta. O
acervo não tem uma única entrada confirmada por falante nativo; deixá-lo tocar
no texto que uma grávida lê seria pôr palavra por validar na boca de quem
assinou outra coisa. Por isso uma correspondência vinda do léxico vale menos do
que uma correspondência directa (`PESO_PONTE_*` em `busca.py`): duas palavras
reconhecidas chegam ao limiar, uma sozinha nunca chega. Se o léxico se enganar
— e vai, com um acervo por validar —, é preciso que o resto da frase o
confirme.

A fronteira é verificável de fora, sem consola, em `/saude/`:

```json
"lexico_emakhuwa": {
  "entradas": 157, "usado_para": "procura",
  "escreve_respostas": false, "validado_por_falante_nativo": false
}
```

### O que a tolerância apaga

A norma de 2014 marca a duração vocálica por duplicação, e ela é distintiva:
*omala* (acabar) e *omaala* (calar-se) são palavras diferentes. A aspiração
também: *ephula* (nariz) e *epula* (chuva). A normalização desta casa funde as
duas coisas.

É uma perda consciente, e o sentido da troca é este: quem escreve é uma mulher
grávida num telemóvel, sem ter aprendido a norma, e a grafia que lhe sai não é
uma escolha. Entre não encontrar um sinal de perigo e encontrar um conteúdo a
mais, a segunda falha é a que se corrige a olhar para o ecrã.

Os pares que a norma distingue e nós fundimos estão fixados em
`apps/assistente/tests.py` (`ParesQueANormalizacaoFundeTest`), junto com um
teste que falha no dia em que os dois membros de um par aparecerem ambos no
conteúdo clínico — altura em que a fusão deixa de ser inofensiva e alguém tem
de decidir.

Continuam distintos, e bem: `h`/`kh` (*hapa* fígado, *khapa* cágado) e
`f`/`ph` (*efuula* flor, *ephula* nariz).

**Achado a devolver ao projecto do dicionário:** a normalização herdada do
acervo v0.2 reduz `ph` a `p` e colapsa vogais dobradas, o que apaga duas
distinções que os documentos normativos marcam como distintivas. Para a busca
compensa; para o dicionário, onde a entrada é a palavra, não compensa — ali a
grafia exacta deve ganhar sempre à normalizada, e ganha, porque o `peso()` do
dicionário tem a correspondência exacta em primeiro lugar. Vale a pena
registar o caso no glossário, na secção «Pares e ambiguidades a vigiar».

## Correr localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py criar_perfis
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

89 testes. Cobrem o cálculo da data prevista do parto, o calendário da OMS, a
regra de validação clínica, a precisão do motor de busca (incluindo perguntas
fora do domínio, que não devem devolver nada), a separação de perfis no painel
de gestão, as cinco camadas da protecção anti-robô e a ausência de dados
pessoais no painel público, nas listagens e no registo de tentativas.

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
apps/gestao/         Painel de gestão próprio, perfis e validação clínica
apps/core/antirobo.py  Protecção anti-robô dos formulários públicos
static/js/app.js     Espelho do motor de busca, para funcionar offline
deploy/              Bloco do Caddy para a VPS partilhada
```

> O algoritmo de `apps/assistente/busca.py` e o de `static/js/app.js` têm de
> permanecer idênticos. Quem alterar um tem de alterar o outro.

## Publicação

Ver [DEPLOY.md](DEPLOY.md).
