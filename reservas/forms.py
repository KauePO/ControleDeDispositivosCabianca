from django import forms
from .models import Categoria, Dispositivo, Reserva, TipoDispositivo
from .services import validar_itens


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ("data", "hora_inicio", "hora_fim", "nome_professor", "observacoes")
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}),
            "hora_fim": forms.TimeInput(attrs={"type": "time"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existentes = {item.tipo_dispositivo_id: item.quantidade for item in self.instance.itens.all()} if self.instance.pk else {}
        for tipo in TipoDispositivo.objects.all():
            self.fields[f"tipo_{tipo.pk}"] = forms.IntegerField(
                label=tipo.nome, min_value=0, required=False, initial=existentes.get(tipo.pk, 0),
            )

    def clean(self):
        cleaned = super().clean()
        if not all(cleaned.get(campo) for campo in ("data", "hora_inicio", "hora_fim")):
            return cleaned
        itens = {int(nome.split("_")[1]): valor for nome, valor in self.cleaned_data.items() if nome.startswith("tipo_") and valor}
        erros = validar_itens(cleaned["data"], cleaned["hora_inicio"], cleaned["hora_fim"], itens, self.instance.pk)
        for chave, mensagem in erros.items():
            if chave != "__all__":
                self.add_error(f"tipo_{chave}", mensagem)
            else:
                self.add_error(None, mensagem)
        if not itens:
            self.add_error(None, "Informe ao menos um dispositivo.")
        return cleaned

    def itens(self):
        return {int(nome.split("_")[1]): valor for nome, valor in self.cleaned_data.items() if nome.startswith("tipo_") and valor}


class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = "__all__"


class DispositivoFilterForm(forms.Form):
    tipo = forms.ModelChoiceField(queryset=TipoDispositivo.objects.all(), required=False, empty_label="Todos os tipos", label="Tipo")
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.all(), required=False, empty_label="Todas as categorias", label="Categoria")


class DashboardFilterForm(forms.Form):
    data = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hora_inicio = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    hora_fim = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    tipo = forms.ModelChoiceField(queryset=TipoDispositivo.objects.all(), required=False, empty_label="Todos os tipos")
    categoria = forms.ModelChoiceField(queryset=Dispositivo.objects.none(), required=False, empty_label="Todas as categorias")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Categoria
        self.fields["categoria"].queryset = Categoria.objects.all()

    def clean(self):
        cleaned = super().clean()
        if bool(cleaned.get("hora_inicio")) != bool(cleaned.get("hora_fim")):
            raise forms.ValidationError("Informe os dois horários para filtrar um intervalo.")
        if cleaned.get("hora_inicio") and cleaned["hora_inicio"] >= cleaned["hora_fim"]:
            raise forms.ValidationError("O horário final deve ser posterior ao inicial.")
        return cleaned
