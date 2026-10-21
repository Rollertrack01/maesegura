# Publicação do MãeSegura

Destino: `maesegura.wooneya.co.mz`, na VPS partilhada `srv1831052`.

Regras da casa que este documento respeita:

- Há **um único Caddy** na VPS, em `/opt/wooneya-backend`. Este projecto não
  traz Caddy nenhum: liga-se à rede `web` e o Caddy existente encaminha para ele.
- O acesso à VPS é pelo **terminal web do hPanel da Hostinger**, não por SSH.
  Por isso os passos abaixo estão em blocos grandes, para colar de uma vez.
- Os passos do Caddy vão sempre encadeados com `&&`, para que uma validação
  falhada impeça a escrita no disco.

---

## Antes de começar

1. Apontar o DNS de `maesegura.wooneya.co.mz` para `187.127.207.84` (registo A).
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
sleep 10 && curl -s -o /dev/null -w "maesegura: %{http_code}\n" https://maesegura.wooneya.co.mz/saude/
```

Se o `caddy validate` falhar, **nada foi aplicado** e o backup está em
`/root/Caddyfile.bak-*`. Reponha com `cp /root/Caddyfile.bak-<data> Caddyfile`.

## 4 — VPS: carregar conteúdo e criar o administrador

```bash
cd /opt/maesegura && \
docker compose -f docker-compose.vps.yml exec maesegura-web python manage.py carregar_conhecimento && \
docker compose -f docker-compose.vps.yml exec maesegura-web python manage.py createsuperuser
```

O conteúdo entra **por validar**. Isso é propositado: até um profissional de
saúde validar em `https://maesegura.wooneya.co.mz/gestao/`, o assistente responde
sempre a encaminhar para a unidade sanitária.

## 5 — Validação clínica

O profissional de saúde entra em `/gestao/`, abre **Conteúdos clínicos**,
revê cada texto e usa a acção **"Marcar como validado por mim, agora"**. O nome
dele fica registado em cada resposta e aparece à utilizadora.

A partir desse momento o painel público mostra o número de conteúdos validados,
que é exactamente o indicador que a candidatura deve apresentar.

## 6 — Verificação que conta

Um 200 não prova que o sistema funciona. Verificar o fluxo inteiro:

```bash
curl -s https://maesegura.wooneya.co.mz/saude/
curl -s https://maesegura.wooneya.co.mz/api/metricas.json
curl -s https://maesegura.wooneya.co.mz/assistente/conhecimento.json | head -c 200
```

E no telemóvel, com dados móveis:

1. Abrir `https://maesegura.wooneya.co.mz`, registar uma gravidez de teste e
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
curl -s -o /dev/null -w "maesegura: %{http_code}\n" https://maesegura.wooneya.co.mz/saude/
```

## Se o servidor morrer

O código está no GitHub e o único estado é a base de dados. Reconstrução:
repetir o passo 2 com o `.env` guardado, restaurar o dump mais recente com
`gunzip -c <ficheiro> | docker compose -f docker-compose.vps.yml exec -T maesegura-db psql -U maesegura maesegura`,
e repetir o passo 3.
