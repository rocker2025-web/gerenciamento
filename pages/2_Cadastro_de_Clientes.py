import streamlit as st
import utils
import uuid
import pandas as pd
from datetime import date

st.set_page_config(page_title="Gerenciamento de Clientes", layout="wide")

# --- VERIFICAÇÃO DE AUTENTICAÇÃO E LOGOUT ---
if not st.session_state.get('autenticado'):
    st.error("Acesso negado. Por favor, realize o login.")
    st.stop()

with st.sidebar:
    st.success(f"Bem-vindo, {st.session_state.get('nome_usuario')}!")
    if st.button("Logout"):
        st.session_state['autenticado'] = False
        # Limpa as variáveis de sessão relacionadas ao CEP e edição ao fazer logout
        for key in ['cep_pesquisado', 'endereco', 'bairro', 'cidade', 'estado', 'editing_client_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("1_Login.py")

st.title("Cadastro e Gerenciamento de Clientes")

# --- CONEXÃO COM BANCO de DADOS de CLIENTES ---
try:
    drive = utils.login_gdrive()
    clients_file = utils.get_database_file(drive, "clients.json")
    clientes_data = utils.read_data(clients_file)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# Inicializa st.session_state.editing_client_id se não existir
if 'editing_client_id' not in st.session_state:
    st.session_state.editing_client_id = None

# --- FUNÇÃO PARA EXCLUIR CLIENTE ---
def excluir_cliente(client_id_to_delete):
    global clientes_data # Para garantir que estamos modificando a lista global
    clientes_antes = len(clientes_data)
    clientes_data = [c for c in clientes_data if c['id'] != client_id_to_delete]
    
    if len(clientes_data) < clientes_antes:
        utils.write_data(clients_file, clientes_data)
        st.success("Cliente excluído com sucesso!")
        # Se estava editando o cliente excluído, sai do modo de edição
        if st.session_state.editing_client_id == client_id_to_delete:
            st.session_state.editing_client_id = None
            for key in ['cep_pesquisado', 'endereco', 'bairro', 'cidade', 'estado', 'numero']:
                if key in st.session_state:
                    del st.session_state[key]
        st.rerun()
    else:
        st.error("Erro: Cliente não encontrado para exclusão.")

# --- BUSCA de CLIENTES ---
st.subheader("Buscar Cliente por CPF/CNPJ")
cpf_cnpj_busca = st.text_input("Digite o CPF ou CNPJ para buscar (com ou sem pontuação)", key="search_cpf_cnpj")
if cpf_cnpj_busca:
    busca_limpa = "".join(filter(str.isdigit, cpf_cnpj_busca))
    clientes_encontrados = []
    if busca_limpa:
        for c in clientes_data:
            doc_armazenado_limpo = "".join(filter(str.isdigit, c.get('cpf_cnpj', '')))
            if busca_limpa in doc_armazenado_limpo:
                clientes_encontrados.append(c)

    if clientes_encontrados:
        st.write(f"{len(clientes_encontrados)} cliente(s) encontrado(s):")
        for cliente in clientes_encontrados:
            with st.expander(f"**{cliente['nome_razao_social']}** - {cliente['cpf_cnpj']}"):
                st.markdown(f"**Tipo:** {cliente['tipo_pessoa']}")
                if cliente.get('data_nascimento'):
                    st.markdown(f"**Data de Nascimento:** {cliente['data_nascimento']}")
                st.markdown(f"**E-mail:** {cliente.get('email', 'N/A')}")
                st.markdown(f"**Telefone:** {cliente.get('telefone', 'N/A')}")
                
                st.markdown("---")
                st.markdown("##### Endereço")
                st.markdown(f"**CEP:** {cliente.get('cep', 'N/A')}")
                st.markdown(f"**Endereço:** {cliente.get('endereco', 'N/A')}")
                
                if cliente.get('bairro'):
                    st.markdown(f"**Bairro:** {cliente.get('bairro', 'N/A')}")
                st.markdown(f"**Cidade/UF:** {cliente.get('cidade', 'N/A')} / {cliente.get('estado', 'N/A')}")
                
                if cliente.get('representante_legal'):
                    rep = cliente['representante_legal']
                    st.markdown("---")
                    st.markdown("##### Representante Legal")
                    st.markdown(f"**Nome:** {rep.get('nome', 'N/A')}")
                    st.markdown(f"**CPF:** {rep.get('cpf', 'N/A')}")
                    st.markdown(f"**Data de Nascimento:** {rep.get('data_nascimento', 'N/A')}")
                    st.markdown(f"**Contato:** {rep.get('telefone', 'N/A')} / {rep.get('email', 'N/A')}")

                st.markdown("---")
                col_btn_busca1, col_btn_busca2 = st.columns(2)
                with col_btn_busca1:
                    if st.button("Editar Cliente", key=f"edit_search_{cliente['id']}", use_container_width=True):
                        st.session_state.editing_client_id = cliente['id']
                        st.rerun()
                with col_btn_busca2:
                    # Botão de exclusão com lógica de confirmação
                    if st.button("Excluir Cliente", key=f"delete_search_{cliente['id']}", use_container_width=True, type="primary"):
                        if st.session_state.get(f"confirm_delete_{cliente['id']}", False): # Se já confirmou
                            excluir_cliente(cliente['id'])
                            st.session_state[f"confirm_delete_{cliente['id']}"] = False # Reseta a confirmação
                        else: # Pede confirmação
                            st.warning(f"Tem certeza que deseja excluir o cliente '{cliente['nome_razao_social']}'? Clique novamente para confirmar.")
                            st.session_state[f"confirm_delete_{cliente['id']}"] = True # Marca para próxima confirmação
                            # Para que o estado seja capturado, talvez precise de um rerun aqui ou de uma lógica mais avançada
                            # Mas para um clique duplo, basta clicar novamente.
    else:
        st.info("Nenhum cliente encontrado com este CPF/CNPJ.")

st.markdown("---")

# --- SEÇÃO DE EDIÇÃO DE CLIENTE ---
if st.session_state.editing_client_id:
    st.subheader("Editar Cliente Existente")
    client_to_edit = next((c for c in clientes_data if c['id'] == st.session_state.editing_client_id), None)

    if client_to_edit:
        full_address = client_to_edit.get('endereco', '')
        address_parts = [p.strip() for p in full_address.split(',', 2)] 
        
        st.session_state.cep_pesquisado = client_to_edit.get('cep', '')
        st.session_state.endereco = address_parts[0] if len(address_parts) > 0 else ''
        st.session_state.numero = address_parts[1] if len(address_parts) > 1 else ''
        st.session_state.bairro = client_to_edit.get('bairro', '')
        st.session_state.cidade = client_to_edit.get('cidade', '')
        st.session_state.estado = client_to_edit.get('estado', '')

        st.markdown("##### 1. Busque o Endereço (Opcional)")
        col_cep_edit1, col_cep_edit2 = st.columns([1, 3])
        with col_cep_edit1:
            cep_lookup_input_edit = st.text_input("Digite o CEP para buscar", value=st.session_state.get('cep_pesquisado', ''), key="cep_lookup_edit")
        with col_cep_edit2:
            if st.button("Buscar Endereço (Edição)", key="buscar_endereco_edit_btn"):
                if cep_lookup_input_edit:
                    dados_cep = utils.consultar_cep(cep_lookup_input_edit)
                    if dados_cep:
                        st.session_state.cep_pesquisado = dados_cep.get('cep', '')
                        st.session_state.endereco = dados_cep.get('logradouro', '')
                        st.session_state.bairro = dados_cep.get('bairro', '')
                        st.session_state.cidade = dados_cep.get('localidade', '')
                        st.session_state.estado = dados_cep.get('uf', '')
                        st.success("Endereço encontrado!")
                    else:
                        st.error("CEP não encontrado ou inválido.")
                else:
                    st.warning("Por favor, insira um CEP para buscar.")
        
        with st.form("editar_cliente_form"):
            st.markdown("##### 2. Edite os Dados do Cliente")
            
            tipo_pessoa_index = 0 if client_to_edit['tipo_pessoa'] == "Pessoa Física" else 1
            tipo_pessoa_edit = st.radio("Tipo de Pessoa", ["Pessoa Física", "Pessoa Jurídica"], horizontal=True, index=tipo_pessoa_index, key="tipo_pessoa_edit")

            st.markdown("###### Dados do Cliente")
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                nome_razao_social_edit = st.text_input("Nome / Razão Social*", value=client_to_edit.get('nome_razao_social', ''), key="nome_razao_social_edit")
                cpf_cnpj_edit = st.text_input("CPF / CNPJ*", value=client_to_edit.get('cpf_cnpj', ''), key="cpf_cnpj_edit")
            with col_edit2:
                email_edit = st.text_input("E-mail", value=client_to_edit.get('email', ''), key="email_edit")
                telefone_edit = st.text_input("Telefone", value=client_to_edit.get('telefone', ''), key="telefone_edit")
            
            st.markdown("###### Endereço")
            cep_edit = st.text_input("CEP", value=st.session_state.get('cep_pesquisado', ''), key="cep_edit")
            endereco_edit = st.text_input("Endereço (Rua/Logradouro)", value=st.session_state.get('endereco', ''), key="endereco_edit")
            
            col_end_edit1, col_end_edit2 = st.columns(2)
            with col_end_edit1:
                numero_edit = st.text_input("Número", value=st.session_state.get('numero', ''), key="numero_edit")
            with col_end_edit2:
                bairro_edit = st.text_input("Bairro", value=st.session_state.get('bairro', ''), key="bairro_edit")

            col_cid_edit, col_est_edit = st.columns(2)
            with col_cid_edit:
                cidade_edit = st.text_input("Cidade", value=st.session_state.get('cidade', ''), key="cidade_edit")
            with col_est_edit:
                estado_edit = st.text_input("Estado (UF)", value=st.session_state.get('estado', ''), key="estado_edit")
            
            data_nascimento_pf_edit = None
            
            if tipo_pessoa_edit == "Pessoa Física":
                if client_to_edit.get('data_nascimento'):
                    try:
                        data_nascimento_pf_edit = date.fromisoformat(client_to_edit['data_nascimento'])
                    except ValueError:
                        data_nascimento_pf_edit = date.today()
                data_nascimento_pf_edit = st.date_input("Data de Nascimento", value=data_nascimento_pf_edit, min_value=date(1900, 1, 1), max_value=date.today(), key="data_nascimento_pf_edit")
            else: # Pessoa Jurídica
                st.markdown("---")
                st.markdown("##### Dados do Representante Legal*")
                rep_legal_data = client_to_edit.get('representante_legal', {}) 
                
                col_rep_edit1, col_rep_edit2 = st.columns(2)
                with col_rep_edit1:
                    rep_nome_edit = st.text_input("Nome do Representante*", value=rep_legal_data.get('nome', ''), key="rep_nome_edit")
                    rep_cpf_edit = st.text_input("CPF do Representante*", value=utils.validar_e_formatar_cpf(rep_legal_data.get('cpf', '')) if rep_legal_data.get('cpf') else '', key="rep_cpf_edit")
                with col_rep_edit2:
                    rep_nascimento_val = None
                    if rep_legal_data.get('data_nascimento'):
                        try:
                            rep_nascimento_val = date.fromisoformat(rep_legal_data['data_nascimento'])
                        except ValueError:
                            rep_nascimento_val = date.today()
                    rep_nascimento_edit = st.date_input("Data de Nascimento do Representante", value=rep_nascimento_val, min_value=date(1900, 1, 1), max_value=date.today(), key="rep_nascimento_edit")
                
                col_rep_edit3, col_rep_edit4 = st.columns(2)
                with col_rep_edit3:
                    rep_telefone_edit = st.text_input("Telefone do Representante", value=rep_legal_data.get('telefone', ''), key="rep_telefone_edit")
                with col_rep_edit4:
                    rep_email_edit = st.text_input("E-mail do Representante", value=rep_legal_data.get('email', ''), key="rep_email_edit")

            submitted_edit = st.form_submit_button("Salvar Edições", use_container_width=True)
        
        # Botão "Cancelar Edição" MOVIDO PARA FORA DO FORMULÁRIO.
        if st.button("Cancelar Edição", use_container_width=True, key="cancel_edit_client_outside_btn"):
            st.session_state.editing_client_id = None
            for key in ['cep_pesquisado', 'endereco', 'bairro', 'cidade', 'estado', 'numero']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        if submitted_edit:
            if not nome_razao_social_edit or not cpf_cnpj_edit:
                st.warning("Nome/Razão Social e CPF/CNPJ são obrigatórios.")
            elif tipo_pessoa_edit == "Pessoa Jurídica" and (not rep_nome_edit or not rep_cpf_edit):
                st.warning("Para Pessoa Jurídica, o Nome e o CPF do Representante Legal são obrigatórios.")
            else:
                doc_formatado_edit = utils.validar_e_formatar_cpf(cpf_cnpj_edit) if tipo_pessoa_edit == "Pessoa Física" else utils.validar_e_formatar_cnpj(cpf_cnpj_edit)
                if not doc_formatado_edit:
                    st.error("CPF ou CNPJ do cliente inválido. Verifique a digitação.")
                else:
                    cpf_cnpj_existente = False
                    for c in clientes_data:
                        if c['id'] != st.session_state.editing_client_id and c['cpf_cnpj'] == doc_formatado_edit:
                            cpf_cnpj_existente = True
                            break
                    
                    if cpf_cnpj_existente:
                        st.error("Este CPF/CNPJ já está cadastrado para outro cliente!")
                    else:
                        endereco_completo_edit = f"{endereco_edit}, {numero_edit}, {bairro_edit}" if numero_edit and bairro_edit else endereco_edit
                        if not numero_edit and bairro_edit:
                            endereco_completo_edit = f"{endereco_edit}, {bairro_edit}"
                        elif not endereco_edit and not numero_edit and not bairro_edit:
                             endereco_completo_edit = ""

                        representante_legal_edit = None
                        if tipo_pessoa_edit == "Pessoa Jurídica":
                            rep_cpf_formatado = utils.validar_e_formatar_cpf(rep_cpf_edit)
                            if not rep_cpf_formatado:
                                st.error("CPF do Representante Legal inválido. Verifique a digitação.")
                                st.stop() 
                            representante_legal_edit = {
                                "nome": rep_nome_edit, "cpf": rep_cpf_formatado, "data_nascimento": str(rep_nascimento_edit),
                                "telefone": rep_telefone_edit, "email": rep_email_edit
                            }
                        
                        for i, c in enumerate(clientes_data):
                            if c['id'] == st.session_state.editing_client_id:
                                clientes_data[i].update({
                                    "tipo_pessoa": tipo_pessoa_edit,
                                    "nome_razao_social": nome_razao_social_edit,
                                    "cpf_cnpj": doc_formatado_edit,
                                    "data_nascimento": str(data_nascimento_pf_edit) if data_nascimento_pf_edit else None,
                                    "email": email_edit,
                                    "telefone": telefone_edit,
                                    "cep": cep_edit,
                                    "cidade": cidade_edit,
                                    "estado": estado_edit,
                                    "endereco": endereco_completo_edit,
                                    "bairro": bairro_edit,
                                    "representante_legal": representante_legal_edit
                                })
                                break
                        
                        utils.write_data(clients_file, clientes_data)
                        st.success(f"Cliente '{nome_razao_social_edit}' atualizado com sucesso!")
                        st.session_state.editing_client_id = None
                        for key in ['cep_pesquisado', 'endereco', 'bairro', 'cidade', 'estado', 'numero']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
    else:
        st.error("Cliente não encontrado para edição.")
        st.session_state.editing_client_id = None

st.markdown("---")

# --- SEÇÃO DE CADASTRO (Só aparece se não estiver no modo de edição) ---
if not st.session_state.editing_client_id:
    st.subheader("Cadastrar Novo Cliente")

    st.markdown("##### 1. Busque o Endereço (Opcional)")
    col_cep1, col_cep2 = st.columns([1, 3])
    with col_cep1:
        cep_lookup_input = st.text_input("Digite o CEP para buscar", key="cep_lookup_new")
    with col_cep2:
        if st.button("Buscar Endereço", key="buscar_endereco_new_btn"):
            if cep_lookup_input:
                dados_cep = utils.consultar_cep(cep_lookup_input)
                if dados_cep:
                    st.session_state.cep_pesquisado = dados_cep.get('cep', '')
                    st.session_state.endereco = dados_cep.get('logradouro', '')
                    st.session_state.bairro = dados_cep.get('bairro', '')
                    st.session_state.cidade = dados_cep.get('localidade', '')
                    st.session_state.estado = dados_cep.get('uf', '')
                    st.success("Endereço encontrado!")
                else:
                    st.error("CEP não encontrado ou inválido.")
            else:
                st.warning("Por favor, insira um CEP para buscar.")

    with st.form("cadastro_cliente_form"):
        st.markdown("##### 2. Preencha os Dados do Cliente")
        tipo_pessoa = st.radio("Tipo de Pessoa", ["Pessoa Física", "Pessoa Jurídica"], horizontal=True, key="tipo_pessoa_new")

        st.markdown("###### Dados do Cliente")
        col1, col2 = st.columns(2)
        with col1:
            nome_razao_social = st.text_input("Nome / Razão Social*", key="nome_razao_social_new")
            cpf_cnpj_input = st.text_input("CPF / CNPJ*", key="cpf_cnpj_new")
        with col2:
            email = st.text_input("E-mail", key="email_new")
            telefone = st.text_input("Telefone", key="telefone_new")
        
        st.markdown("###### Endereço")
        cep = st.text_input("CEP", value=st.session_state.get('cep_pesquisado', ''), key="cep_new")
        endereco = st.text_input("Endereço (Rua/Logradouro)", value=st.session_state.get('endereco', ''), key="endereco_new")
        
        col_end1, col_end2 = st.columns(2)
        with col_end1:
            numero = st.text_input("Número", key="numero_new")
        with col_end2:
            bairro = st.text_input("Bairro", value=st.session_state.get('bairro', ''), key="bairro_new")

        col_cid, col_est = st.columns(2)
        with col_cid:
            cidade = st.text_input("Cidade", value=st.session_state.get('cidade', ''), key="cidade_new")
        with col_est:
            estado = st.text_input("Estado (UF)", value=st.session_state.get('estado', ''), key="estado_new")
        
        data_nascimento_pf, representante_legal = None, None
        
        if tipo_pessoa == "Pessoa Física":
            data_nascimento_pf = st.date_input("Data de Nascimento", min_value=date(1900, 1, 1), max_value=date.today(), key="data_nascimento_pf_new")
        else:
            st.markdown("---")
            st.markdown("##### Dados do Representante Legal*")
            col_rep1, col_rep2 = st.columns(2)
            with col_rep1:
                rep_nome = st.text_input("Nome do Representante*", key="rep_nome_new")
                rep_cpf = st.text_input("CPF do Representante*", key="rep_cpf_new")
            with col_rep2:
                rep_nascimento = st.date_input("Data de Nascimento do Representante", min_value=date(1900, 1, 1), max_value=date.today(), key="rep_nascimento_new")
            
            col_rep3, col_rep4 = st.columns(2)
            with col_rep3:
                rep_telefone = st.text_input("Telefone do Representante", key="rep_telefone_new")
            with col_rep4:
                rep_email = st.text_input("E-mail do Representante", key="rep_email_new")

        submitted = st.form_submit_button("Salvar Cliente")

        if submitted:
            if not nome_razao_social or not cpf_cnpj_input:
                st.warning("Nome/Razão Social e CPF/CNPJ são obrigatórios.")
            elif tipo_pessoa == "Pessoa Jurídica" and (not rep_nome or not rep_cpf):
                st.warning("Para Pessoa Jurídica, o Nome e o CPF do Representante Legal são obrigatórios.")
            else:
                doc_formatado = utils.validar_e_formatar_cpf(cpf_cnpj_input) if tipo_pessoa == "Pessoa Física" else utils.validar_e_formatar_cnpj(cpf_cnpj_input)
                if not doc_formatado:
                    st.error("CPF ou CNPJ do cliente inválido. Verifique a digitação.")
                else:
                    if any(c['cpf_cnpj'] == doc_formatado for c in clientes_data):
                        st.error("Este CPF/CNPJ já está cadastrado!")
                    else:
                        endereco_completo = f"{endereco}, {numero}, {bairro}" if numero and bairro else endereco
                        if not numero and bairro:
                            endereco_completo = f"{endereco}, {bairro}"
                        elif not endereco and not numero and not bairro:
                             endereco_completo = ""

                        if tipo_pessoa == "Pessoa Jurídica":
                            rep_cpf_formatado = utils.validar_e_formatar_cpf(rep_cpf)
                            if not rep_cpf_formatado:
                                st.error("CPF do Representante Legal inválido. Verifique a digitação.")
                                st.stop()
                            representante_legal = {"nome": rep_nome, "cpf": rep_cpf_formatado, "data_nascimento": str(rep_nascimento), "telefone": rep_telefone, "email": rep_email}
                        
                        novo_cliente = {
                            "id": str(uuid.uuid4()), "tipo_pessoa": tipo_pessoa, "nome_razao_social": nome_razao_social,
                            "cpf_cnpj": doc_formatado, "data_nascimento": str(data_nascimento_pf) if data_nascimento_pf else None,
                            "email": email, "telefone": telefone, "cep": cep, "cidade": cidade, "estado": estado,
                            "endereco": endereco_completo, "bairro": bairro,
                            "representante_legal": representante_legal
                        }
                        clientes_data.append(novo_cliente)
                        utils.write_data(clients_file, clientes_data)
                        st.success(f"Cliente '{nome_razao_social}' salvo com sucesso!")
                        
                        for key in ['cep_pesquisado', 'endereco', 'bairro', 'cidade', 'estado']:
                            if key in st.session_state: del st.session_state[key]
                        st.rerun()

st.markdown("---")

# --- LISTA DE CLIENTES CADASTRADOS ---
st.subheader("Clientes Cadastrados")
if clientes_data:
    clientes_ordenados = sorted(clientes_data, key=lambda c: c['nome_razao_social'])
    for cliente in clientes_ordenados:
        with st.expander(f"**{cliente['nome_razao_social']}** - {cliente['cpf_cnpj']}"):
            st.markdown(f"**Tipo:** {cliente['tipo_pessoa']}")
            if cliente.get('data_nascimento'):
                st.markdown(f"**Data de Nascimento:** {cliente['data_nascimento']}")
            
            st.markdown(f"**E-mail:** {cliente.get('email', 'N/A')}")
            st.markdown(f"**Telefone:** {cliente.get('telefone', 'N/A')}")
            
            st.markdown("---")
            st.markdown("##### Endereço")
            st.markdown(f"**CEP:** {cliente.get('cep', 'N/A')}")
            st.markdown(f"**Endereço:** {cliente.get('endereco', 'N/A')}")
            
            if cliente.get('bairro'):
                st.markdown(f"**Bairro:** {cliente.get('bairro', 'N/A')}")
            st.markdown(f"**Cidade/UF:** {cliente.get('cidade', 'N/A')} / {cliente.get('estado', 'N/A')}")
            
            if cliente.get('representante_legal'):
                rep = cliente['representante_legal']
                st.markdown("---")
                st.markdown("##### Representante Legal")
                st.markdown(f"**Nome:** {rep.get('nome', 'N/A')}")
                st.markdown(f"**CPF:** {rep.get('cpf', 'N/A')}")
                st.markdown(f"**Data de Nascimento:** {rep.get('data_nascimento', 'N/A')}")
                st.markdown(f"**Contato:** {rep.get('telefone', 'N/A')} / {rep.get('email', 'N/A')}")

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Editar Cliente", key=f"edit_{cliente['id']}", use_container_width=True):
                    st.session_state.editing_client_id = cliente['id']
                    st.rerun()
            with col2:
                # Botão de exclusão com lógica de confirmação
                if st.button("Excluir Cliente", key=f"delete_{cliente['id']}", use_container_width=True, type="primary"):
                    # O Streamlit lida com cliques duplos sequenciais se o estado não for resetado rapidamente
                    if st.session_state.get(f"confirm_delete_{cliente['id']}", False): 
                        excluir_cliente(cliente['id'])
                        # Resetar a flag de confirmação para este cliente após a exclusão
                        st.session_state[f"confirm_delete_{cliente['id']}"] = False 
                    else:
                        st.warning(f"Tem certeza que deseja excluir o cliente '{cliente['nome_razao_social']}'? Clique novamente no botão para confirmar.")
                        # Marcar a flag de confirmação para o próximo clique
                        st.session_state[f"confirm_delete_{cliente['id']}"] = True 
                        # Isso fará com que o aviso apareça e o usuário tenha que clicar novamente.
                        # Não precisa de rerun aqui, o Streamlit já re-renderiza o botão.
else:
    st.info("Nenhum cliente cadastrado ainda.")

utils.exibir_rodape()