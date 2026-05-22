import pyodbc
from ksef_generator import KsefGenerator
import os
import config
import traceback

conn_string = config.get_conn_string()

def pobierz_komplet_do_ksef(numer_faktury):
    print(f"\n--- Start procesu dla faktury: {numer_faktury} ---")
    try:
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()

        # 1. FIRMA
        print("Pobieranie danych sprzedawcy...")
        query_firma = """
            SELECT adr_NazwaPelna, adr_Nazwa, adr_NIP, adr_Miejscowosc, adr_Adres, adr_Kod, p.pa_KodPanstwaISO as adr_SymbolKraju
            FROM adr__Ewid a
            LEFT JOIN sl_Panstwo p ON a.adr_IdPanstwo = p.pa_Id
            WHERE a.adr_IdObiektu = 1 AND a.adr_TypAdresu = 8
        """
        cursor.execute(query_firma)
        row_firma = cursor.fetchone()
        if not row_firma:
            print("❌ BŁĄD: Nie znaleziono danych sprzedawcy!")
            return
        
        cols_firma = [c[0] for c in cursor.description]
        moja_firma = dict(zip(cols_firma, row_firma))
        print(f"✅ Dane sprzedawcy pobrane: {moja_firma.get('adr_Nazwa')}")

        # 2. NAGŁÓWEK
        print("Pobieranie nagłówka faktury...")
        query_naglowek = """
            SELECT 
                d.dok_Id, d.dok_NrPelny, 
                d.dok_DataWyst, d.dok_DataMag,
                adr.adr_NazwaPelna, adr.adr_Nazwa, adr.adr_NIP, adr.adr_Miejscowosc, adr.adr_Adres, adr.adr_Kod, p.pa_KodPanstwaISO as adr_SymbolKraju,
                d.dok_WartNetto, d.dok_WartVat, d.dok_WartBrutto,
                d.dok_WartNettoWal, d.dok_WartVatWal, d.dok_WartBruttoWal,
                d.dok_PlatTermin,
                ISNULL(d.dok_Waluta, 'PLN') as dok_Waluta, d.dok_WalutaKurs
            FROM dok__Dokument d
            LEFT JOIN adr__Ewid adr ON d.dok_PlatnikId = adr.adr_IdObiektu AND adr.adr_TypAdresu = 1
            LEFT JOIN sl_Panstwo p ON adr.adr_IdPanstwo = p.pa_Id
            WHERE d.dok_NrPelny = ? AND d.dok_Typ = 2
        """
        cursor.execute(query_naglowek, numer_faktury)
        row_nag = cursor.fetchone()
        if not row_nag:
            print(f"❌ BŁĄD: Nie znaleziono faktury {numer_faktury}!")
            return
        
        cols_nag = [c[0] for c in cursor.description]
        naglowek = dict(zip(cols_nag, row_nag))
        print(f"✅ Nagłówek pobrany. Waluta: {naglowek['dok_Waluta']}, Kurs: {naglowek['dok_WalutaKurs']}")

        # 3. TABELA VAT
        print("Pobieranie tabeli VAT...")
        query_tabela_vat = """
            SELECT 
                v.vat_Id, v.vat_Stawka, v.vat_Symbol,
                SUM(p.ob_WartNetto) AS SumaNetto, 
                SUM(p.ob_WartVat) AS SumaVat
            FROM dok_Pozycja p
            JOIN sl_StawkaVAT v ON p.ob_VatId = v.vat_Id
            WHERE p.ob_DokHanId = ?
            GROUP BY v.vat_Id, v.vat_Stawka, v.vat_Symbol
        """
        cursor.execute(query_tabela_vat, naglowek['dok_Id'])
        rows_vat = cursor.fetchall()
        cols_vat = [c[0] for c in cursor.description]
        tabela_vat = [dict(zip(cols_vat, r)) for r in rows_vat]
        print(f"✅ Tabela VAT: {len(tabela_vat)} stawek.")

        # 4. POZYCJE
        print("Pobieranie pozycji...")
        query_pozycje = """
            SELECT 
                t.tw_Nazwa, p.ob_Ilosc, p.ob_Jm, 
                p.ob_CenaNetto, p.ob_WartNetto, p.ob_WartVat, p.ob_WartBrutto,
                v.vat_Id, v.vat_Stawka, v.vat_Symbol, t.tw_Rodzaj
            FROM dok_Pozycja p
            LEFT JOIN tw__Towar t ON p.ob_TowId = t.tw_Id
            JOIN sl_StawkaVAT v ON p.ob_VatId = v.vat_Id
            WHERE p.ob_DokHanId = ?
        """
        cursor.execute(query_pozycje, naglowek['dok_Id'])
        rows_poz = cursor.fetchall()
        cols_poz = [c[0] for c in cursor.description]
        pozycje = [dict(zip(cols_poz, r)) for r in rows_poz]
        print(f"✅ Pobrano {len(pozycje)} pozycji.")

        # 5. GENEROWANIE
        print("Uruchamianie generatora KSeF...")
        gen = KsefGenerator()
        xml_data = gen.generate(moja_firma, naglowek, tabela_vat, pozycje)

        # 6. ZAPIS
        filename = f"KSeF_{naglowek['dok_NrPelny'].replace('/', '_').replace(' ', '_')}.xml"
        gen.save(xml_data, filename)
        print(f"🎉 SUKCES! Plik zapisany jako: {filename}\n")

        conn.close()

    except Exception as e:
        print(f"❌ KRYTYCZNY BŁĄD w pobierz_komplet_do_ksef: {e}")
        print("Szczegóły błędu:")
        print(traceback.format_exc())

if __name__ == "__main__":
    try:
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()
        print("Szukam ostatniej faktury FS...")
        cursor.execute("SELECT TOP 1 dok_NrPelny FROM dok__Dokument WHERE dok_Typ = 2 ORDER BY dok_DataWyst DESC, dok_Id DESC")
        row = cursor.fetchone()
        conn.close()

        if row:
            nr = row[0]
            pobierz_komplet_do_ksef(nr)
        else:
            print("Nie znaleziono żadnych faktur w bazie.")
    except Exception as e:
        print(f"❌ Błąd startowy: {e}")
        print(traceback.format_exc())
