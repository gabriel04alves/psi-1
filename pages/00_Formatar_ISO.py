import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))


def _get_extractor():
    try:
        from get_and_format_iso import extract as extractor
    except SystemExit as exc:
        st.error(str(exc))
        return None
    except Exception as exc:
        st.error(f"Erro ao carregar extrator: {exc}")
        return None
    return extractor


st.set_page_config(
    page_title="Formatar ISO | PSI",
    page_icon="🧰",
    layout="wide",
)

st.title("🧰 Formatar ISO a partir de PDF")
st.markdown(
    "Converta um PDF de norma ISO (padrão ABNT) no formato exigido pelo sistema."
)

st.markdown("---")

st.subheader("1. Envie o PDF")
uploaded = st.file_uploader(
    "Selecione um PDF da norma",
    type=["pdf"],
    label_visibility="collapsed",
)

col1, col2 = st.columns([2, 1])
with col1:
    output_name = st.text_input(
        "Nome do arquivo de saída",
        value="controles_iso.json",
        help="O arquivo será gerado no formato JSON compatível com a ingestão.",
    )
with col2:
    st.caption("Formato de saída: JSON")

st.subheader("2. Gerar arquivo no formato do PSI")

if uploaded:
    if st.button("Extrir conteúdo do PDF", type="primary", icon="⚙️"):
        with st.spinner("Extraindo controles..."):
            extractor = _get_extractor()
            if extractor is None:
                st.stop()
            temp_pdf = None
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as temp_pdf:
                    temp_pdf.write(uploaded.read())
                    temp_path = Path(temp_pdf.name)

                log_buffer = io.StringIO()
                with redirect_stdout(log_buffer):
                    controles = extractor(str(temp_path))

                if not controles:
                    st.error(
                        "Nenhum controle foi extraido. Verifique se o PDF "
                        "segue o padrao ABNT com 'Controle' em linha propria."
                    )
                else:
                    temas = {c["tema"] for c in controles}
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("Controles extraidos", len(controles))
                    col_m2.metric("Temas detectados", len(temas))
                    col_m3.metric("Arquivo de saida", output_name)

                    df = pd.DataFrame(controles)
                    cols = [
                        c
                        for c in [
                            "id",
                            "tema",
                            "tema_nome",
                            "nome",
                            "descricao",
                            "proposito",
                        ]
                        if c in df.columns
                    ]
                    df = df[cols]
                    st.dataframe(df, use_container_width=True, height=320)

                    output_bytes = json.dumps(
                        controles, ensure_ascii=False, indent=2
                    ).encode("utf-8")

                    st.download_button(
                        "Baixar JSON formatado",
                        data=output_bytes,
                        file_name=output_name,
                        mime="application/json",
                        type="primary",
                        icon="⬇️",
                    )

                    with st.expander("Ver log de processamento"):
                        st.text(log_buffer.getvalue().strip())
            finally:
                if temp_pdf and Path(temp_pdf.name).exists():
                    Path(temp_pdf.name).unlink(missing_ok=True)

st.markdown("---")
st.markdown(
    "**Como usar depois:** Baixe o JSON e importe na pagina **Ingestao de Dados**."
)
