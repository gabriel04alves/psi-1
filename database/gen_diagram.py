from eralchemy2 import render_er
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "auditoria.db"


def gerar_diagrama():
    """Gera um diagrama ER a partir do banco SQLite gerado."""
    # O ERAlchemy precisa do caminho no formato de URL do SQLAlchemy
    db_url = f"sqlite:///{DB_PATH}"

    # Define onde salvar a imagem (vamos colocar na mesma pasta do banco)
    output_path = DB_PATH.parent / "diagrama_modelo.png"

    print("Gerando diagrama ER...")
    try:
        # render_er recebe a origem (o banco) e o destino (a imagem)
        render_er(db_url, str(output_path))
        print(f"Diagrama gerado com sucesso em: {output_path}")
    except Exception as e:
        print(f"Erro ao gerar o diagrama: {e}")


if __name__ == "__main__":
    gerar_diagrama()
