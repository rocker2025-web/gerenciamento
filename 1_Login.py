# 1_Login.py
import streamlit as st
import utils
import base64 # Biblioteca para codificar a imagem

st.set_page_config(page_title="Login - Rocker Equipamentos", layout="centered")

# --- FUNÇÃO PARA CARREGAR E CODIFICAR A IMAGEM ---
def get_image_as_base64(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

# Carrega a imagem da logo
logo_path = "assets/logo.png"
logo_base64 = get_image_as_base64(logo_path)

# --- ESTILOS CSS PARA APLICAR A FONTE POPPINS E AJUSTAR TAMANHOS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
    
    .title {
        font-family: 'Poppins', sans-serif;
        font-size: 2.8em; /* Tamanho da fonte aumentado */
        font-weight: 700;
        text-align: center;
    }
    .centered-image {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- CABEÇALHO CENTRALIZADO COM LOGO E TÍTULO ---
if logo_base64:
    st.markdown(
        f'<img src="data:image/png;base64,{logo_base64}" alt="Rocker Equipamentos Logo" class="centered-image" width="500">',
        unsafe_allow_html=True
    )

st.markdown('<h1 class="title">Gerenciamento de Clientes</h1>', unsafe_allow_html=True)


# Se já estiver autenticado, redireciona para a página de cadastro
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if st.session_state['autenticado']:
    st.switch_page("pages/2_Cadastro_de_Clientes.py")

# --- FORMULÁRIO DE LOGIN ---
with st.form("login_form"):
    email = st.text_input("E-mail de Acesso")
    senha = st.text_input("Senha", type="password")
    submitted = st.form_submit_button("Entrar")

    if submitted:
        # Conexão com o banco de dados de usuários movida para dentro da submissão
        try:
            drive = utils.login_gdrive()
            users_file = utils.get_database_file(drive, "users.json")
            users_data = utils.read_data(users_file)
            
            usuario_encontrado = None
            for user in users_data:
                if user['email'] == email and user['senha'] == senha:
                    usuario_encontrado = user
                    break
            
            if usuario_encontrado:
                st.session_state['autenticado'] = True
                st.session_state['nome_usuario'] = usuario_encontrado['nome']
                st.success("Login realizado com sucesso!")
                st.switch_page("pages/2_Cadastro_de_Clientes.py")
            else:
                st.error("E-mail ou senha incorretos.")

        except Exception as e:
            st.error(f"Falha na conexão ou autenticação. Verifique sua rede e tente novamente. Erro: {e}")

utils.exibir_rodape()