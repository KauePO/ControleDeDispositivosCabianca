from datetime import time

from django import forms
from .models import Categoria, Dispositivo, Reserva, TipoDispositivo
from .services import validar_itens


class ReservaForm(forms.ModelForm):
    OPCOES_HORARIO = (
        ("07:10", "7:10"),
        ("08:00", "8:00"),
        ("08:50", "8:50"),
        ("09:55", "9:55"),
        ("10:45", "10:45"),
        ("11:35", "11:35"),
        ("13:30", "13:30"),
        ("14:20", "14:20"),
        ("15:10", "15:10"),
    )
    horarios = forms.MultipleChoiceField(
        label="Horários",
        choices=OPCOES_HORARIO,
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Selecione ao menos dois horários."},
    )

    class Meta:
        model = Reserva
        fields = ("data", "nome_professor", "observacoes")
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._horarios_iniciais = []
        self._horario_original = None
        if self.instance.pk:
            opcoes = [valor for valor, _ in self.OPCOES_HORARIO]
            inicio = self.instance.hora_inicio.strftime("%H:%M")
            fim = self.instance.hora_fim.strftime("%H:%M")
            inicio_index = max((i for i, valor in enumerate(opcoes) if valor <= inicio), default=0)
            fim_index = min((i for i, valor in enumerate(opcoes) if valor >= fim), default=len(opcoes) - 1)
            if fim_index <= inicio_index:
                if inicio_index == len(opcoes) - 1:
                    inicio_index -= 1
                else:
                    fim_index = inicio_index + 1
            self._horarios_iniciais = opcoes[inicio_index:fim_index + 1]
            self._horario_original = (self.instance.hora_inicio, self.instance.hora_fim)
            self.initial["horarios"] = self._horarios_iniciais

        existentes = {item.tipo_dispositivo_id: item.quantidade for item in self.instance.itens.all()} if self.instance.pk else {}
        for tipo in TipoDispositivo.objects.all():
            self.fields[f"tipo_{tipo.pk}"] = forms.IntegerField(
                label=tipo.nome, min_value=0, required=False, initial=existentes.get(tipo.pk, 0),
            )

    def clean(self):
        cleaned = super().clean()
        selecionados = cleaned.get("horarios", [])
        if len(selecionados) < 2:
            if "horarios" not in self.errors:
                self.add_error("horarios", "Selecione pelo menos dois horários para definir o período.")
            return cleaned

        ordem = [valor for valor, _ in self.OPCOES_HORARIO]
        indices = sorted(ordem.index(valor) for valor in selecionados)
        if indices != list(range(indices[0], indices[-1] + 1)):
            self.add_error("horarios", "Selecione horários consecutivos para formar um período contínuo.")
            return cleaned

        selecionados_ordenados = [ordem[indice] for indice in indices]
        if self._horario_original and selecionados_ordenados == self._horarios_iniciais:
            hora_inicio, hora_fim = self._horario_original
        else:
            hora_inicio = time.fromisoformat(selecionados_ordenados[0])
            hora_fim = time.fromisoformat(selecionados_ordenados[-1])
        cleaned["hora_inicio"] = hora_inicio
        cleaned["hora_fim"] = hora_fim
        self.instance.hora_inicio = hora_inicio
        self.instance.hora_fim = hora_fim
        if not cleaned.get("data"):
            return cleaned

        itens = {int(nome.split("_")[1]): valor for nome, valor in self.cleaned_data.items() if nome.startswith("tipo_") and valor}
        erros = validar_itens(cleaned["data"], hora_inicio, hora_fim, itens, self.instance.pk)
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
