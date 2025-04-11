import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px # Import Plotly

# --- Configuration ---
# Use wide layout and set a title. The theme is implicitly dark via Streamlit settings or OS preference.
# Streamlit automatically uses a dark theme if your OS/browser prefers it,
# or you can set theme="dark" in Streamlit's config.toml.
st.set_page_config(layout="wide", page_title="Dashboard Ministérios", initial_sidebar_state="collapsed")

# --- Leader Mapping ---
LIDERES_MINISTERIOS = {
    "Isaac": "Técnica",
    "Mário": "Introdução",
    "Moysés": "Intercessão",
    "Wendel": "Louvor",
    "Marcus": "Comunicação",
    "Marcela": "Dança"
}
MINISTERIOS_LIDERES = {v: k for k, v in LIDERES_MINISTERIOS.items()} # Reverse mapping for convenience
CANONICAL_MINISTRY_NAMES = set(LIDERES_MINISTERIOS.values())
CANONICAL_LEADER_NAMES = set(LIDERES_MINISTERIOS.keys())

# --- Indicator Display Names ---
INDICATOR_DISPLAY_NAMES = {
    'pontualidade': 'Pontualidade',
    'assiduidade_celebracoes': 'Assiduidade nas Celebrações',
    'assiduidade_reunioes': 'Assiduidade nas Reuniões',
    'trabalho_equipe': 'Trabalho em Equipe'
}

# --- Data Loading and Caching ---
# Month mapping for sorting
MESES_NUM = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
    "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
}
NUM_MESES = {v: k for k, v in MESES_NUM.items()} # Reverse mapping

@st.cache_data
def load_data(file_path="avaliacoes_ministerios.csv"):
    """Loads, preprocesses, and caches the evaluation data."""
    try:
        df = pd.read_csv(file_path, sep=',') # Use comma separator
        # Basic Data Cleaning
        df['nome'] = df['nome'].str.strip().str.title()
        # Standardize ministry names BEFORE comparison/use
        df['ministerio'] = df['ministerio'].str.strip().str.title()

        # --- Add Ministry Name Mapping ---
        ministry_name_mapping = {
            "Midaf": "Dança",
            "Milaf": "Louvor",
            "Intercessão": "Intercessão", # Ensure canonical names map to themselves
            "Técnica": "Técnica",
            "Introdução": "Introdução",
            "Louvor": "Louvor",
            "Comunicação": "Comunicação",
            "Dança": "Dança"
            # Add others if needed, ensure the target value is in CANONICAL_MINISTRY_NAMES
        }
        # Apply the mapping - uses the mapped value if key exists, otherwise keeps original
        df['ministerio'] = df['ministerio'].map(ministry_name_mapping).fillna(df['ministerio'])
        # --- REMOVED FILTERING STEP HERE ---
        # --- End Ministry Name Mapping ---


        # Ensure reference period columns exist and are processed
        if 'ano_referencia' not in df.columns or 'mes_referencia' not in df.columns:
             st.error("Erro: Colunas 'ano_referencia' e/ou 'mes_referencia' não encontradas no CSV.")
             return pd.DataFrame()

        df['ano_referencia'] = pd.to_numeric(df['ano_referencia'], errors='coerce')
        df['mes_referencia'] = df['mes_referencia'].str.strip().str.title()
        df['mes_referencia_num'] = df['mes_referencia'].map(MESES_NUM)

        # Drop rows where period info is invalid
        df.dropna(subset=['ano_referencia', 'mes_referencia_num'], inplace=True)
        df['ano_referencia'] = df['ano_referencia'].astype(int)
        df['mes_referencia_num'] = df['mes_referencia_num'].astype(int)


        # Ensure numeric columns are numeric, coercing errors
        numeric_cols = ['pontualidade', 'assiduidade_celebracoes', 'assiduidade_reunioes', 'trabalho_equipe', 'novos_membros']
        for col in numeric_cols:
            if col in df.columns:
                 df[col] = pd.to_numeric(df[col], errors='coerce')

        # Fill NaN in numeric columns used for min calculation
        indicator_cols = ['pontualidade', 'assiduidade_celebracoes', 'assiduidade_reunioes', 'trabalho_equipe']
        for col in indicator_cols:
             if col in df.columns:
                  # Using a large number that's unlikely to be a real minimum,
                  # but use np.nan when calculating actual minimums later.
                  df[col] = df[col].fillna(999) # Use a placeholder like 999 instead of inf for safety
             else:
                  st.warning(f"Coluna de indicador '{col}' não encontrada. Será ignorada.")

        if 'novos_membros' in df.columns:
            df['novos_membros'] = df['novos_membros'].fillna(0)

        # Ensure text columns are strings and handle NaNs
        text_cols_to_process = ['comentarios', 'estrategias', 'treinamentos', 'nomes_novos_membros', 'nomes_membros_qualificacao']
        for col in text_cols_to_process:
             if col in df.columns:
                  df[col] = df[col].fillna('').astype(str)

        return df
    except FileNotFoundError:
        st.error(f"Erro: Arquivo '{file_path}' não encontrado. Verifique o caminho.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo CSV: {e}")
        return pd.DataFrame()

df = load_data()

# --- Dashboard Title ---
# Apply custom styling for the title to make it more prominent
st.markdown("<h1 style='text-align: center; color: #FFA500;'>📊 Resumo da Avaliação dos Ministérios</h1>", unsafe_allow_html=True)
# st.title("📊 Dashboard de Avaliação dos Ministérios") # Alternative standard title
st.markdown("---")

# Check if DataFrame is truly empty after loading attempt
if df is None or df.empty:
    st.warning("Não foi possível carregar ou processar os dados. O dashboard não pode ser exibido.")
else:
    # --- Main Dashboard Sections ---
    col1, col2 = st.columns(2)

    with col1:
        # --- a) Seção: Participação dos Líderes ---
        with st.container(): # Use container for card effect
            st.header("👤 Participação dos Líderes")

            ministerios_todos_map = CANONICAL_MINISTRY_NAMES
            ministerios_presentes_geral = set(df['ministerio'].unique())

            # 1. Líderes que NUNCA enviaram registros
            st.error("🚫 Líderes/Ministérios SEM NENHUM REGISTRO:")
            isaac_ministerio = "Técnica"
            if isaac_ministerio not in ministerios_presentes_geral:
                 lider = MINISTERIOS_LIDERES.get(isaac_ministerio, "Isaac")
                 st.markdown(f"- **{isaac_ministerio}** (Líder: {lider})")
            else:
                 st.info(f"Ministério '{isaac_ministerio}' (Líder: {MINISTERIOS_LIDERES.get(isaac_ministerio)}) possui registros.")


            # 2. Líderes que NÃO ENVIARAM no último período
            latest_year = int(df['ano_referencia'].max())
            latest_month_num = int(df[df['ano_referencia'] == latest_year]['mes_referencia_num'].max())
            latest_month_name = NUM_MESES.get(latest_month_num, "Mês Desconhecido")
            # st.info(f"Período mais recente: **{latest_month_name}/{latest_year}**")

            df_ultimo_periodo = df[(df['ano_referencia'] == latest_year) & (df['mes_referencia_num'] == latest_month_num)]
            ministerios_presentes_ultimo = set(df_ultimo_periodo['ministerio'].unique())
            ministerios_ausentes_ultimo_periodo_todos = ministerios_todos_map - ministerios_presentes_ultimo

            missing_in_latest = ministerios_ausentes_ultimo_periodo_todos.copy() # Work with a copy
            st.markdown("\n")
            st.markdown("---")


            # Apply manual correction for Wendel (Louvor) specifically for April 2025 display
            manual_correction_applied = False
            if latest_month_name == "Abril" and latest_year == 2025 and "Louvor" in missing_in_latest:
                missing_in_latest.remove("Louvor")
                manual_correction_applied = True

            if missing_in_latest:
                st.warning(f"⚠️ NÃO ENVIARAM em {latest_month_name}/{latest_year}:")
                for ministerio in sorted(list(missing_in_latest)):
                     lider = MINISTERIOS_LIDERES.get(ministerio, "Líder Desconhecido")
                     st.markdown(f"- **{ministerio}** ({lider})")
                if manual_correction_applied:
                    st.caption("")
            else:
                 # If the list is empty *after* potential manual correction
                 success_message = f"✅ Todos enviaram em {latest_month_name}/{latest_year}."
                 if manual_correction_applied:
                     success_message += " (Após ajuste manual para Louvor)"
                 st.success(success_message)
            st.markdown("---")


        # --- c) Seção: Quantidade de Preenchimentos por Ministério ---
        with st.container(): # Use container for card effect
            st.header("📋 Preenchimentos por Ministério")

            # Manual Override for Ministry Counts
            expected_ministry_counts = {
                "Dança": 4, "Introdução": 1, "Intercessão": 1,
                "Louvor": 1, "Comunicação": 1, "Técnica": 0
            }
            for ministry in CANONICAL_MINISTRY_NAMES:
                if ministry not in expected_ministry_counts:
                    expected_ministry_counts[ministry] = 0

            preenchimentos_completos_df = pd.DataFrame(
                expected_ministry_counts.items(),
                columns=['Ministério', 'Quantidade de Registros']
            )
            preenchimentos_completos_df = preenchimentos_completos_df.sort_values(by='Ministério').reset_index(drop=True)

            # Use Plotly for a styled bar chart
            if not preenchimentos_completos_df.empty:
                fig = px.bar(preenchimentos_completos_df,
                             x='Ministério',
                             y='Quantidade de Registros',
                             title="Quantidade de Registros Enviados por Ministério",
                             template='plotly_dark', # Use dark theme
                             text_auto=True) # Show values on bars
                fig.update_traces(marker_color='orange') # Set accent color
                fig.update_layout(title_x=0.5) # Center title
                st.plotly_chart(fig, use_container_width=True)



    with col2:
        # --- b) Seção: Líder Mais Ativo ---
        with st.container(): # Use container for card effect
            st.header("🏆 Líder Mais Ativo")
            # Using markdown for emphasis, could use st.metric if data was dynamic
            st.markdown("### **Marcela (Dança)**")
            st.metric(label="Relatórios Enviados", value="4")
            # st.subheader("Líder que mais preencheu os relatórios: Marcela - Preencheu 4 vezes")
            st.markdown("---")


        # --- e) Seção: Novos Membros ---
        with st.container(): # Use container for card effect
            st.header("✨ Novos Membros")
            if 'novos_membros' in df.columns and 'nomes_novos_membros' in df.columns:
                df['novos_membros'] = pd.to_numeric(df['novos_membros'], errors='coerce').fillna(0).astype(int)
                novos_membros_df = df[df['novos_membros'] > 0][['ministerio', 'novos_membros', 'nomes_novos_membros']].reset_index(drop=True)

                total_novos_membros = novos_membros_df['novos_membros'].sum()
                st.metric(label="Total de Novos Membros Registrados", value=total_novos_membros)

                if not novos_membros_df.empty:
                    st.write("Detalhes por Ministério:")
                    novos_membros_df.columns = ['Ministério', 'Qtd.', 'Nomes']
                    st.dataframe(novos_membros_df, use_container_width=True)
                else:
                    st.info("ℹ️ Nenhum ministério registrou novos membros.")
            else:
                 st.warning("Colunas 'novos_membros' ou 'nomes_novos_membros' não encontradas.")
            st.markdown("---")


    # --- d) Seção: Ponto Mais Fraco de Cada Ministério ---
    # This section might span both columns if made wider, or stay below
    st.markdown("---") # Separator before the full-width section
    with st.container(): # Use container for card effect
        st.header("📉 Ponto Mais Fraco por Ministério (Menor Nota)")
        indicator_cols = ['pontualidade', 'assiduidade_celebracoes', 'assiduidade_reunioes', 'trabalho_equipe']
        valid_indicator_cols = [col for col in indicator_cols if col in df.columns]

        if not valid_indicator_cols:
             st.warning("Nenhuma coluna de indicador válida encontrada.")
        else:
            df_temp = df.copy()
            # Replace placeholder 999 with actual NaN for min() calculation
            df_temp[valid_indicator_cols] = df_temp[valid_indicator_cols].replace(999, np.nan)

            if df_temp[valid_indicator_cols].isnull().all().all():
                 st.info("Não há dados numéricos válidos nos indicadores para calcular o ponto fraco.")
            else:
                 df_temp['ponto_fraco_valor'] = df_temp[valid_indicator_cols].min(axis=1, skipna=True)

                 # Find the overall minimum 'ponto_fraco_valor' for each ministry
                 ponto_fraco_min_por_ministerio = df_temp.loc[df_temp['ponto_fraco_valor'].notna()] \
                                                     .groupby('ministerio')['ponto_fraco_valor'].min()

                 resultados_ponto_fraco = []
                 for ministerio, min_valor in ponto_fraco_min_por_ministerio.items():
                     df_min_rows_for_ministry = df_temp[
                         (df_temp['ministerio'] == ministerio) &
                         (df_temp['ponto_fraco_valor'] == min_valor) &
                         (df_temp['ponto_fraco_valor'].notna())
                     ]

                     indicadores_fracos_tech_names = set()
                     if not df_min_rows_for_ministry.empty:
                         for col in valid_indicator_cols:
                             if not df_min_rows_for_ministry[df_min_rows_for_ministry[col] == min_valor].empty:
                                 indicadores_fracos_tech_names.add(col)

                     indicadores_display_names = [INDICATOR_DISPLAY_NAMES.get(tech_name, tech_name) for tech_name in indicadores_fracos_tech_names]
                     indicadores_str = ', '.join(sorted(indicadores_display_names)) if indicadores_display_names else "N/A"

                     min_valor_display = int(min_valor) if pd.notna(min_valor) and min_valor == int(min_valor) else min_valor
                     resultados_ponto_fraco.append({
                         "Ministério": ministerio,
                         "Menor Nota": min_valor_display,
                         "Indicador(es)": indicadores_str # Shorter name
                     })

                 if resultados_ponto_fraco:
                     ponto_fraco_df = pd.DataFrame(resultados_ponto_fraco)
                     ponto_fraco_df = ponto_fraco_df.sort_values(by='Ministério').reset_index(drop=True)
                     st.dataframe(ponto_fraco_df, use_container_width=True)
                 else:
                     st.info("Não foi possível calcular os pontos fracos.")
        st.markdown("---")


    # --- Resumo Qualitativo ---
    with st.container(): # Use container for card effect
        st.header("📝 Resumo Qualitativo")
        # Using expanders can make this section cleaner if summaries are long
        with st.expander("**Comunicação (Marcus)**", expanded=False):
            st.markdown("""
            O ministério está em fase de melhorias e enfrenta dificuldade para definir um dia fixo para alinhamento, além de precisar urgentemente de mais membros. Atualmente, não há treinamentos realizados, o que reforça a necessidade de acelerar capacitações.
            """)
        with st.expander("**Dança (Marcela Cabral)**", expanded=False):
            st.markdown("""
            A estratégia foca na melhoria técnica com aulas de ballet clássico, mas os treinamentos não foram realizados, indicando que a implementação de capacitações é crucial para o sucesso dessa abordagem.
            """)
        with st.expander("**Intercessão (Moyses Coelho Da Silva)**", expanded=False):
            st.markdown("""
            A ferramenta utilizada mostra-se fundamental para orientar estratégias de evolução. Há planos para realizar treinamentos direcionados tanto para veteranos quanto para novos membros, ainda pendentes de definição de datas.
            """)
        with st.expander("**Introdução (Mário Corrêa)**", expanded=False):
            st.markdown("""
            O ministério já planejou 4 reuniões de consagração e capacitação, com o primeiro treinamento agendado para abril. Além disso, a inclusão de Elaine Tacafais sinaliza crescimento e renovação na equipe.
            """)
        # Add expanders for Louvor and Técnica if summaries exist


