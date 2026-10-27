# Publicação do MãeSegura

Destino: `maesegura.energisa.co.mz`, na VPS partilhada `srv1831052`.

O domínio oficial é o da **Energisa**, a empresa candidata à chamada do UNICEF.
O antigo `maesegura.wooneya.co.mz` continua a responder, mas apenas a
reencaminhar para o novo, para que nenhuma ligação já partilhada quebre.

Dois endereços de administração, de propósito: `/gestao/` é o painel próprio,
onde a equipa clínica e a coordenação trabalham; `/sistema/` é o Django admin,
só para manutenção técnica do superuser.

Regras da casa que este documento respeita:

- Há **um único Caddy** na VPS, em `/opt/wooneya-backend`. Este projecto não
  traz Caddy nenhum: liga-se à rede `web` e o Caddy existente encaminha para ele.
- O acesso à VPS é pelo **terminal web do hPanel da Hostinger**, não por SSH.
  Por isso os passos abaixo estão em blocos grandes, para colar de uma vez.
- Os passos do Caddy vão sempre encadeados com `&&`, para que uma validação
  falhada impeça a escrita no disco.

---

## Antes de começar

1. Apontar o DNS de `maesegura.energisa.co.mz` para `187.127.207.84` (registo A).
2. Publicar o repositório **público** no GitHub (a licença aberta é requisito do
   UNICEF; o repositório privado não serve para a candidatura).
3. Criar uma chave de deploy só de leitura nesse repositório.

## 1 — Windows: publicar o código no GitHub

Descompactar o ZIP para `C:\Users\UNIROVUMA\Downloads\maesegura` e, no
PowerShell:

```powershell
cd C:\Users\UNIROVUMA\Downloads\maesegura
git init
git config user.name "Gentil Francisco Supia Bira"
git config user.email "gentilfranciscomaia@gmail.com"
git add .
git commit -m "feat: protótipo MãeSegura — acompanhamento materno bilingue offline"
git branch -M main
git remote add origin https://github.com/Rollertrack01/maesegura.git
git push -u origin main
```

O repositório tem de ficar **público** e com o ficheiro `LICENSE` (MIT) na raiz.

## 2 — VPS: instalar

Bloco único no terminal web do hPanel:

```bash
mkdir -p /opt/maesegura && cd /opt/maesegura && \
git clone git@github-maesegura:Rollertrack01/maesegura.git . && \
cp .env.example .env && \
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n')|" .env && \
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" .env && \
docker compose -f docker-compose.vps.yml up -d --build && \
sleep 30 && docker compose -f docker-compose.vps.yml ps
```

Confirmar que os dois contentores aparecem `healthy`. Se `maesegura-web` ficar
`unhealthy`, ver a causa antes de seguir:

```bash
docker logs --tail 50 maesegura-web
```

## 3 — VPS: ligar o Caddy

O bloco a acrescentar está em `deploy/caddy-maesegura.txt`. Passos encadeados,
com validação antes da escrita:

```bash
cd /opt/wooneya-backend && \
cp Caddyfile /root/Caddyfile.bak-$(date +%F-%H%M) && \
cat /opt/maesegura/deploy/caddy-maesegura.txt >> Caddyfile && \
docker run --rm -v /opt/wooneya-backend/Caddyfile:/etc/caddy/Caddyfile:ro caddy:latest caddy validate --config /etc/caddy/Caddyfile && \
docker restart wooneya-backend-caddy-1 && \
sleep 10 && curl -s -o /dev/null -w "maesegura: %{http_code}\n" https://maesegura.energisa.co.mz/saude/
```

Se o `caddy validate` falhar, **nada foi aplicado** e o backup está em
`/root/Caddyfile.bak-*`. Reponha com `cp /root/Caddyfile.bak-<data> Caddyfile`.

## 4 — VPS: carregar conteúdo e criar o administrador

```bash
cd /opt/maesegura && \
docker compose -f docker-compose.vps.yml exec maesegura-web python manage.py criar_perfis && \
docker compose -f docker-compose.vps.yml exec maesegura-web python manage.py carregar_conhecimento && \
docker compose -f docker-compose.vps.yml exec maesegura-web python manage.py createsuperuser
```

O `criar_perfis` cria os dois perfis do painel: **Clínico** e **Gestor**. O
`createsuperuser` cria a conta técnica, que é a única com acesso ao Django admin
em `/sistema/` e à secção **Equipa e perfis**, onde se criam as contas das
restantes pessoas.

O conteúdo entra **por validar**. Isso é propositado: até um profissional de
saúde validar em `https://maesegura.energisa.co.mz/gestao/`, o assistente responde
sempre a encaminhar para a unidade sanitária.

## 5 — Contas e validação clínica

Entre em `https://maesegura.energisa.co.mz/gestao/` com a conta técnica e abra
**Equipa e perfis**. Crie uma conta de perfil **Clínico** para o profissional de
saúde e uma de perfil **Gestor** para a coordenação. Preencha o nome completo:
é esse nome que fica gravado em cada resposta validada e é mostrado à grávida.

O profissional de saúde entra com a sua conta, abre **Conteúdos**, filtra por
**Por validar**, revê cada texto contra as normas do MISAU e carrega em
**Validar**. O gestor não vê esse botão: coordenar e assinar são funções
diferentes, e só quem tem competência clínica assina.

A partir desse momento o painel público mostra o número de conteúdos validados,
que é exactamente o indicador que a candidatura deve apresentar.

## 6 — Verificação que conta

Um 200 não prova que o sistema funciona. Verificar o fluxo inteiro:

```bash
curl -s https://maesegura.energisa.co.mz/saude/
curl -s https://maesegura.energisa.co.mz/api/metricas.json
curl -s https://maesegura.energisa.co.mz/assistente/conhecimento.json | head -c 200
```

E no telemóvel, com dados móveis:

1. Abrir `https://maesegura.energisa.co.mz`, registar uma gravidez de teste e
   confirmar que aparecem as consultas certas.
2. Fazer uma pergunta com sinal de perigo e confirmar o encaminhamento.
3. Instalar a aplicação ("Adicionar ao ecrã principal").
4. **Desligar os dados móveis**, abrir a aplicação e fazer outra pergunta. Tem
   de responder a partir do conteúdo guardado e mostrar o aviso de falta de rede.
5. Confirmar que `/painel/` subiu os números.

O passo 4 é o que demonstra o requisito de baixo consumo de dados. É o que vale
a pena filmar para o vídeo da candidatura.

## Cópias de segurança

```bash
docker compose -f docker-compose.vps.yml exec -T maesegura-db \
  pg_dump -U maesegura maesegura | gzip > /root/backups/maesegura-$(date +%F).sql.gz
```

Pôr em cron diário e **testar um restauro** antes de considerar o backup feito.

## Actualizar depois de uma alteração

```bash
cd /opt/maesegura && git pull && \
docker compose -f docker-compose.vps.yml up -d --build && \
sleep 25 && docker compose -f docker-compose.vps.yml ps && \
curl -s -o /dev/null -w "maesegura: %{http_code}\n" https://maesegura.energisa.co.mz/saude/
```

## Se o servidor morrer

O código está no GitHub e o único estado é a base de dados. Reconstrução:
repetir o passo 2 com o `.env` guardado, restaurar o dump mais recente com
`gunzip -c <ficheiro> | docker compose -f docker-compose.vps.yml exec -T maesegura-db psql -U maesegura maesegura`,
e repetir o passo 3.

---

## Nota sobre redes Docker nesta VPS

A `srv1831052` esgotou as reservas de endereços que o Docker usa para criar
redes automaticamente: as quinze sub-redes /16 de `172.17`–`172.31` e as
dezasseis /20 de `192.168.x` estão todas atribuídas. Um `docker compose up` de
um projecto novo falha com:

```
failed to create network <projecto>_interna: Error response from daemon:
all predefined address pools have been fully subnetted
```

Por isso o `docker-compose.vps.yml` deste projecto **declara a sua subrede**
(`192.168.240.0/24`), em vez de a pedir ao Docker. Antes de instalar outro
projecto na mesma VPS, confirmar que a subrede escolhida não colide:

```bash
docker network inspect $(docker network ls -q) \
  --format '{{.Name}}  {{range .IPAM.Config}}{{.Subnet}}{{end}}  (contentores: {{len .Containers}})' | sort
```

Paliativo imediato: `docker network prune -f` liberta as redes sem contentores
ligados. Correcção de fundo, para uma janela de manutenção e **não** a meio de
uma instalação (reinicia todos os contentores da VPS): alargar as reservas em
`/etc/docker/daemon.json` com `default-address-pools` e reiniciar o Docker.

---

## Mudar para o domínio da Energisa (sistema já instalado)

Feito o registo A de `maesegura` em `energisa.co.mz` a apontar para
`187.127.207.84`, são três passos.

**1. Deixar o Django aceitar o novo domínio.** Sem isto responde `400 Bad
Request`, porque o `ALLOWED_HOSTS` não o conhece:

```bash
cd /opt/maesegura && \
sed -i 's|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=maesegura.energisa.co.mz,maesegura.wooneya.co.mz,localhost|' .env && \
sed -i 's|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://maesegura.energisa.co.mz,https://maesegura.wooneya.co.mz|' .env && \
grep -E '^(ALLOWED_HOSTS|CSRF_TRUSTED_ORIGINS)=' .env
```

**2. Trocar o bloco do Caddy.** O bloco antigo sai e entra o novo par: domínio
da Energisa mais o reencaminhamento do antigo. Com validação antes de qualquer
escrita no Caddy vivo:

```bash
cd /opt/wooneya-backend && \
cp Caddyfile /root/Caddyfile.bak-$(date +%F-%H%M) && \
python3 -c "
import pathlib, re
p = pathlib.Path('/opt/wooneya-backend/Caddyfile')
t = p.read_text()
t = re.sub(r'\nmaesegura\.[^\s{]+ \{.*?\n\}\n', '\n', t, flags=re.S)
t = t.rstrip() + '\n\n' + pathlib.Path('/opt/maesegura/deploy/caddy-maesegura.txt').read_text()
p.write_text(t)
print('Caddyfile preparado')
" && \
docker run --rm -v /opt/wooneya-backend/Caddyfile:/etc/caddy/Caddyfile:ro caddy:latest caddy validate --config /etc/caddy/Caddyfile && \
docker restart wooneya-backend-caddy-1
```

**3. Reiniciar a aplicação e verificar:**

```bash
cd /opt/maesegura && docker compose -f docker-compose.vps.yml up -d && sleep 20 && \
curl -s -o /dev/null -w "energisa: %{http_code}\n" https://maesegura.energisa.co.mz/saude/ && \
curl -s -o /dev/null -w "wooneya (espera 301): %{http_code}\n" https://maesegura.wooneya.co.mz/saude/
```

Se o `caddy validate` falhar, nada foi aplicado ao Caddy vivo e o backup está em
`/root/Caddyfile.bak-*`.

---

## Protecção anti-robô

Os quatro pontos de entrada públicos — registo, assistente, entrada por código e
login do painel — têm cinco camadas:

| Camada | O que faz |
|---|---|
| Campo-armadilha | Campo escondido; se vier preenchido, responde como sucesso e não grava nada |
| Carimbo assinado | Recusa envios sem carimbo, com assinatura inválida ou rápidos demais |
| Limite por IP | Registo 40/h, assistente 60/h, entrada por código 10/h, login 30/h |
| Bloqueio de senhas | 10 erradas por IP ou 5 por conta em 15 min bloqueiam, mesmo com a senha certa |
| Turnstile | Opcional, só com chaves no `.env` |

Os limites do registo e do assistente são generosos de propósito: uma unidade
sanitária inteira partilha a mesma ligação, e um agente comunitário de saúde
pode registar várias mulheres seguidas. O da entrada por código é apertado,
porque é o único ponto onde alguém poderia procurar à força o registo de saúde
de outra mulher.

O service worker passou a ir à rede primeiro nas páginas. Sem isso, uma página
guardada no telemóvel traria um carimbo e um token CSRF velhos, e o envio
seguinte seria recusado sem a mulher perceber porquê.

A página **Segurança** do painel (`/gestao/seguranca/`, só superuser) mostra o
que foi bloqueado, por motivo, por formulário e por endereço.

### Ligar o Cloudflare Turnstile (opcional)

1. `dash.cloudflare.com` › Turnstile › **Add widget**, modo **Managed**,
   domínio `maesegura.energisa.co.mz`.
2. Na VPS, pôr as duas chaves no `.env` e reiniciar a aplicação:

```bash
cd /opt/maesegura && nano .env
docker compose -f docker-compose.vps.yml up -d maesegura-web
```

3. Confirmar em `/gestao/seguranca/` que o aviso "por ligar" desapareceu.

### Limpeza do registo

As tentativas com mais de 90 dias apagam-se com:

```bash
cd /opt/maesegura && \
docker compose -f docker-compose.vps.yml exec maesegura-web python manage.py limpar_tentativas
```

Vale a pena pôr isto no cron, uma vez por mês.

### Verificação que conta

1. Abrir o registo e o assistente: funcionam exactamente como antes.
2. `/gestao/seguranca/` abre e mostra o registo de tentativas.
3. Cinco senhas erradas numa conta de teste bloqueiam 15 minutos, **mesmo
   depois de acertar na senha**.
4. Onze tentativas seguidas de entrada por código devolvem o aviso de limite.
