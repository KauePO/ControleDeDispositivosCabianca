from django import forms
from .horarios import AULAS_CHOICES, AULAS_POR_NUMERO, aulas_que_sobrepoem
from .models import Categoria, Dispositivo, Reserva, TipoDispositivo
from .services import validar_itens


class ReservaForm(forms.ModelForm):
    aulas = forms.MultipleChoiceField(
        label="Aulas",
        choices=AULAS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Selecione pelo menos uma aula."},
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
        self._aulas_iniciais = []
        self._intervalo_original = None
        self._preservar_intervalo_legado = False
        if self.instance.pk:
            aulas_salvas = list(self.instance.aulas.values_list("numero_aula", flat=True))
            if aulas_salvas:
                self._aulas_iniciais = [str(numero) for numero in aulas_salvas]
            else:
                self._aulas_iniciais = [
                    str(numero)
                    for numero in aulas_que_sobrepoem(self.instance.hora_inicio, self.instance.hora_fim)
                ]
            self._intervalo_original = (self.instance.hora_inicio, self.instance.hora_fim)
            self.initial["aulas"] = self._aulas_iniciais

        existentes = {item.tipo_dispositivo_id: item.quantidade for item in self.instance.itens.all()} if self.instance.pk else {}
        for tipo in TipoDispositivo.objects.all():
            self.fields[f"tipo_{tipo.pk}"] = forms.IntegerField(
                label=tipo.nome, min_value=0, required=False, initial=existentes.get(tipo.pk, 0),
            )

    def clean(self):
        cleaned = super().clean()
        selecionados = cleaned.get("aulas", [])
        if not selecionados:
            if "aulas" not in self.errors:
                self.add_error("aulas", "Selecione pelo menos uma aula para reservar.")
            return cleaned

        numeros_aulas = sorted(int(numero) for numero in selecionados)
        if self._intervalo_original and [str(numero) for numero in numeros_aulas] == self._aulas_iniciais:
            hora_inicio, hora_fim = self._intervalo_original
            self._preservar_intervalo_legado = not self.instance.aulas.exists()
        else:
            primeira_aula = AULAS_POR_NUMERO[numeros_aulas[0]]
            ultima_aula = AULAS_POR_NUMERO[numeros_aulas[-1]]
            hora_inicio, hora_fim = primeira_aula["inicio"], ultima_aula["fim"]
        cleaned["hora_inicio"] = hora_inicio
        cleaned["hora_fim"] = hora_fim
        cleaned["numeros_aulas"] = numeros_aulas
        self.instance.hora_inicio = hora_inicio
        self.instance.hora_fim = hora_fim
        if not cleaned.get("data"):
            return cleaned

        itens = {int(nome.split("_")[1]): valor for nome, valor in self.cleaned_data.items() if nome.startswith("tipo_") and valor}
        erros = validar_itens(cleaned["data"], hora_inicio, hora_fim, itens, self.instance.pk, numeros_aulas)
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

    def numeros_aulas(self):
        return self.cleaned_data["numeros_aulas"]



class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = "__all__"
        widgets = {
            "comentarios": forms.Textarea(attrs={"rows": 2, "placeholder": "Adicione comentários relevantes sobre o dispositivo"}),
        }


class DispositivoFilterForm(forms.Form):
    tipo = forms.ModelChoiceField(queryset=TipoDispositivo.objects.all(), required=False, empty_label="Todos os tipos", label="Tipo")
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.all(), required=False, empty_label="Todas as categorias", label="Categoria")


class DashboardFilterForm(forms.Form):
    data = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    aulas = forms.MultipleChoiceField(
        label="Aulas",
        choices=AULAS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    tipo = forms.ModelChoiceField(queryset=TipoDispositivo.objects.all(), required=False, empty_label="Todos os tipos")
    categoria = forms.ModelChoiceField(queryset=Dispositivo.objects.none(), required=False, empty_label="Todas as categorias")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Categoria
        self.fields["categoria"].queryset = Categoria.objects.all()

    def clean(self):
        cleaned = super().clean()
        selecionados = cleaned.get("aulas", [])
        if selecionados:
            numeros_aulas = sorted(int(numero) for numero in selecionados)
            cleaned["numeros_aulas"] = numeros_aulas
            cleaned["hora_inicio"] = AULAS_POR_NUMERO[numeros_aulas[0]]["inicio"]
            cleaned["hora_fim"] = AULAS_POR_NUMERO[numeros_aulas[-1]]["fim"]
        return cleaned
