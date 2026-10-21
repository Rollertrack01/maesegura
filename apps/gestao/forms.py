from django import forms
from django.contrib.auth.models import Group, User

from apps.acompanhamento.models import UnidadeSanitaria
from apps.assistente.models import Conhecimento

from .perfis import PERFIS


class ConteudoForm(forms.ModelForm):
    class Meta:
        model = Conhecimento
        fields = [
            "topico", "gravidade", "destaque",
            "pergunta_pt", "resposta_pt", "palavras_chave_pt",
            "pergunta_vmw", "resposta_vmw", "palavras_chave_vmw",
            "traducao_vmw_validada", "fonte",
        ]
        widgets = {
            "resposta_pt": forms.Textarea(attrs={"rows": 7}),
            "resposta_vmw": forms.Textarea(attrs={"rows": 7}),
            "palavras_chave_pt": forms.Textarea(attrs={"rows": 3}),
            "palavras_chave_vmw": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "topico": "Tópico",
            "gravidade": "Gravidade",
            "destaque": "Mostrar nas perguntas frequentes",
            "pergunta_pt": "Pergunta (português)",
            "resposta_pt": "Resposta (português)",
            "palavras_chave_pt": "Palavras-chave (português)",
            "pergunta_vmw": "Pergunta (Emakhuwa)",
            "resposta_vmw": "Resposta (Emakhuwa)",
            "palavras_chave_vmw": "Palavras-chave (Emakhuwa)",
            "traducao_vmw_validada": "Tradução revista por falante nativo",
            "fonte": "Fonte clínica",
        }
        help_texts = {
            "palavras_chave_pt": "Separadas por vírgula. Escreva como a mulher escreveria, não termos técnicos.",
            "fonte": "Norma ou documento de origem. Ex.: OMS, Recomendações ANC 2016.",
        }

    def clean_resposta_pt(self):
        texto = self.cleaned_data["resposta_pt"].strip()
        if len(texto) < 40:
            raise forms.ValidationError(
                "A resposta é curta demais para ser útil a quem está assustada. "
                "Diga o que fazer, não apenas o que é."
            )
        return texto


class UnidadeForm(forms.ModelForm):
    class Meta:
        model = UnidadeSanitaria
        fields = ["nome", "distrito", "tipo", "telefone", "confirmado_em"]
        widgets = {"confirmado_em": forms.DateInput(attrs={"type": "date"})}
        labels = {
            "nome": "Nome da unidade",
            "distrito": "Distrito",
            "tipo": "Tipo",
            "telefone": "Telefone",
            "confirmado_em": "Data em que o contacto foi confirmado",
        }
        help_texts = {
            "confirmado_em": (
                "Sem esta data a unidade não aparece às utilizadoras. "
                "Só preencha depois de telefonar e confirmar."
            ),
        }


class UtilizadorForm(forms.ModelForm):
    perfil = forms.ChoiceField(
        choices=[(p, p) for p in PERFIS], label="Perfil", help_text=(
            "Clínico valida conteúdo e assina as respostas. Gestor acompanha "
            "indicadores e unidades sanitárias, mas não pode validar conteúdo clínico."
        )
    )
    senha = forms.CharField(
        widget=forms.PasswordInput, min_length=10, label="Senha",
        help_text="Mínimo 10 caracteres.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        labels = {
            "username": "Nome de utilizador",
            "first_name": "Nome",
            "last_name": "Apelido",
            "email": "Email",
        }
        help_texts = {
            "first_name": "O nome completo aparece nas respostas que esta pessoa validar.",
        }

    def save(self, commit=True):
        utilizador = super().save(commit=False)
        utilizador.set_password(self.cleaned_data["senha"])
        utilizador.is_staff = False
        utilizador.save()
        grupo = Group.objects.get(name=self.cleaned_data["perfil"])
        utilizador.groups.set([grupo])
        return utilizador
