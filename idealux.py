# streamlit_app.py
import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Generatore Listino Kaufland 🇩🇪", layout="wide")
st.title("🏷️idel lux_to Kaufland")

# Configurazioni nazionali
NAZIONI = {
    "Germania": {
        "id_shipping_group": 101587,
        "valuta": "EUR",
        "spedizioni": [(1, 8.97), (2, 9.86), (3, 10.74), (5, 11.72), (10, 13.03), (15, 15.02), (20, 16.90), (25, 21.09), (30, 22.98)]
    },
    "Slovacchia": {
        "id_shipping_group": 120271,
        "valuta": "EUR",
        "spedizioni": [(3, 12.14), (5, 17.97), (10, 25.56), (15, 43.06), (20, 50.91), (30, 60.90)]
    },
    "Repubblica Ceca": {
        "id_shipping_group": 120272,
        "valuta": "CZK",
        "spedizioni": [(3, 12.14), (5, 17.97), (10, 25.56), (15, 43.06), (20, 50.91), (30, 60.90)],
        "usa_cambio": True
    },
    "Polonia": {
        "id_shipping_group": 102590,
        "valuta": "PLN",
        "spedizioni": [(1, 8.11), (2, 9.66), (3, 11.21), (5, 13.73), (10, 15.57), (15, 18.47), (20, 21.12), (25, 29.77), (30, 32.43)]
    },
    "Austria": {
        "id_shipping_group": 102095,
        "valuta": "EUR",
        "spedizioni": [(1, 9.60), (2, 10.61), (3, 11.63), (5, 12.73), (10, 13.80), (15, 15.41), (20, 16.87), (25, 21.74), (30, 23.70)]
    },
    "Italia": {
        "id_shipping_group": 111588,
        "valuta": "EUR",
        "spedizioni": [(2, 5.71), (3, 5.81), (5, 7.02), (10, 9.66), (25, 13.92), (30, 21.73)]
    },
    "Francia": {
        "id_shipping_group": 120273,
        "valuta": "EUR",
        "spedizioni": [(1, 9.98), (2, 10.99), (3, 12.02), (5, 13.15), (10, 15.88), (15, 18.01), (20, 20.03), (25, 24.83), (30, 26.85)]
    }
}

def calcola_spedizione_generica(peso_reale, volume_m3, soglie):
    volume_cm3 = volume_m3 * 1_000_000
    peso_volumetrico = volume_cm3 / 5000
    peso_effettivo = max(peso_reale, peso_volumetrico)

    if peso_effettivo > 30:
        return None

    for soglia, costo in soglie:
        if peso_effettivo <= soglia:
            return costo
    return None

def arrotonda_psicologicamente(prezzo):
    intero = int(prezzo)
    centesimi = prezzo - intero
    if centesimi >= 0.50:
        return intero + 0.99
    else:
        return max(0, intero - 1 + 0.99)

# Scelta nazione
target_nazione = st.selectbox("🌍 Seleziona il Paese di destinazione", list(NAZIONI.keys()))
config = NAZIONI[target_nazione]
valuta = config["valuta"]
id_shipping_group = config["id_shipping_group"]
spedizioni = config["spedizioni"]

tasso_cambio = 1.0
if valuta != "EUR":
    tasso_cambio = st.number_input(
        f"💱 Tasso di cambio EUR → {valuta}",
        min_value=0.01, value=1.0, step=0.01
    )

# Upload file Excel
uploaded_file = st.file_uploader("📂 Carica il file Excel del fornitore (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ File caricato con successo!")

    # Nuovi parametri configurabili richiesti dall'utente
    spedizione_fascia_eur = st.number_input("🚚 Spedizione aggiuntiva per fascia 1-20€ (€)", min_value=0.0, value=5.0)
    diff_prezzo_eur = st.number_input("↔️ Differenza tra prezzo massimo e minimo (€)", min_value=0.0, value=5.0)
    stock_minimo = st.number_input("📦 Stock minimo", min_value=0, value=1)

    colonne_richieste = ["Nr", "Prezzo netto", "Peso Lordo", "Volume Scatola", "Magazzino", "Prezzo Al Pubblico"]

    if not all(col in df.columns for col in colonne_richieste):
        st.error("❌ Il file non contiene tutte le colonne necessarie: " + ", ".join(colonne_richieste))
    else:
        output_rows = []

        for _, row in df.iterrows():
            try:
                ean = str(row["Nr"]).strip()
                prezzo_netto = float(row["Prezzo netto"])
                peso_lordo = float(row["Peso Lordo"])
                volume_m3 = float(row["Volume Scatola"])
                count = int(row["Magazzino"])
                prezzo_pubblico_eur = float(row["Prezzo Al Pubblico"])

                if count < stock_minimo:
                    continue

                spedizione = calcola_spedizione_generica(peso_lordo, volume_m3, spedizioni)
                if spedizione is None:
                    continue

                # Calcolo per l'id_offer (rimasto invariato come da richiesta)
                prezzo_convertito = prezzo_netto * tasso_cambio
                spedizione_convertita = spedizione * tasso_cambio

                # Logica del prezzo minimo a partire da "Prezzo Al Pubblico"
                prezzo_base_eur = prezzo_pubblico_eur
                if 1.00 <= prezzo_base_eur <= 20.00:
                    prezzo_base_eur += spedizione_fascia_eur

                # Conversione in valuta target
                prezzo_minimo = prezzo_base_eur * tasso_cambio
                
                # Calcolo prezzo massimo (differenza anch'essa convertita in valuta)
                prezzo_massimo = prezzo_minimo + (diff_prezzo_eur * tasso_cambio)

                # Arrotondamento applicato SOLO al prezzo massimo
                prezzo_massimo = arrotonda_psicologicamente(prezzo_massimo)

                # Conversione in centesimi
                price = int(round(prezzo_massimo * 100))
                minimum_price = int(round(prezzo_minimo * 100))

                id_offer = f"idealux_{ean}_{int(prezzo_convertito + spedizione_convertita)}"

                output_rows.append({
                    "ean": ean,
                    "condition": 100,
                    "price": price,
                    "currency": valuta,
                    "comment": "",
                    "id_offer": id_offer,
                    "id_warehouse": 57331,
                    "count": count,
                    "minimum_price": minimum_price,
                    "price_cs": "",
                    "minimum_price_cs": "",
                    "id_shipping_group": id_shipping_group,
                    "handling_time": 1
                })

            except Exception as e:
                st.warning(f"⚠️ Errore nella riga con EAN {row.get('Nr')}: {e}")
                continue

        if output_rows:
            df_final = pd.DataFrame(output_rows)

            prefissi = {
                "Germania": "de",
                "Slovacchia": "sk",
                "Repubblica Ceca": "cz",
                "Polonia": "pl",
                "Austria": "at",
                "Italia": "it",
                "Francia": "fr"
            }

            now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            prefix = prefissi.get(target_nazione, "xx")
            nome_file = f"{prefix}_idealux_{now}.csv"

            csv_data = df_final.to_csv(index=False, sep=";")

            st.download_button(
                label="📥 Scarica listino",
                data=csv_data,
                file_name=nome_file,
                mime="text/csv"
            )

            st.success(f"✅ File generato correttamente: `{nome_file}`")
            st.dataframe(df_final.head(20), use_container_width=True)
        else:
            st.warning("⚠️ Nessun prodotto valido trovato dopo i filtri.")
