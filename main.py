import pyodbc
from ksef_generator import KsefGenerator
import os
import config

conn_string = config.get_conn_string()

def pobierz_komplet_do_ksef(numer_faktury):
    try:
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()

        query_firma = """
            SELECT adr_Nazwa, adr_NIP, adr_Miejscowosc, adr_Adres, adr_Kod, p.pa_KodPanstwaISO as adr_SymbolKraju
            FROM adr__Ewid a
            LEFT JOIN sl_Panstwo p ON a.adr_IdPanstwo = p.pa_Id
            WHERE a.adr_IdObiektu = 1 AND a.adr_TypAdresu = 8
        """
        cursor.execute(query_firma)
        moja_firma = cursor.fetchone()

        if not moja_firma:
            print("Uwaga: Nie znaleziono danych sprzedawcy w bazie!")
            return

        query_naglowek = """
            SELECT 
                d.dok_Id, d.dok_NrPelny, 
                d.dok_DataWyst, d.dok_DataMag,
                adr.adr_Nazwa, adr.adr_NIP, adr.adr_Miejscowosc, adr.adr_Adres, adr.adr_Kod, p.pa_KodPanstwaISO as adr_SymbolKraju,
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
        naglowek = cursor.fetchone()

        if not naglowek:
            print("Nie znaleziono faktury!")
            return

        query_tabela_vat = """
            SELECT 
                v.vat_Id, v.vat_Stawka, 
                SUM(p.ob_WartNetto) AS SumaNetto, 
                SUM(p.ob_WartVat) AS SumaVat
            FROM dok_Pozycja p
            JOIN sl_StawkaVAT v ON p.ob_VatId = v.vat_Id
            WHERE p.ob_DokHanId = ?
            GROUP BY v.vat_Id, v.vat_Stawka
        """
        cursor.execute(query_tabela_vat, naglowek.dok_Id)
        tabela_vat = cursor.fetchall()

        query_pozycje = """
            SELECT 
                t.tw_Nazwa, p.ob_Ilosc, p.ob_Jm, 
                p.ob_CenaNetto, p.ob_WartNetto, p.ob_WartVat, p.ob_WartBrutto,
                v.vat_Id, v.vat_Stawka
            FROM dok_Pozycja p
            LEFT JOIN tw__Towar t ON p.ob_TowId = t.tw_Id
            JOIN sl_StawkaVAT v ON p.ob_VatId = v.vat_Id
            WHERE p.ob_DokHanId = ?
        """
        cursor.execute(query_pozycje, naglowek.dok_Id)
        pozycje = cursor.fetchall()

        gen = KsefGenerator()
        xml_data = gen.generate(moja_firma, naglowek, tabela_vat, pozycje)

        filename = f"KSeF_{naglowek.dok_NrPelny.replace('/', '_')}.xml"
        gen.save(xml_data, filename)

        print(f"Sukces! Wygenerowano plik KSeF dla faktury {naglowek.dok_NrPelny}")

        conn.close()

    except Exception as e:
        print(f"Błąd: {e}")

if __name__ == "__main__":
    try:
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 dok_NrPelny FROM dok__Dokument WHERE dok_Typ = 2 ORDER BY dok_DataWyst DESC, dok_Id DESC")
        row = cursor.fetchone()
        conn.close()

        if row:
            ostatni_numer = row.dok_NrPelny
            print(f"Przetwarzanie ostatniej faktury: {ostatni_numer}")
            pobierz_komplet_do_ksef(ostatni_numer)
        else:
            print("Nie znaleziono żadnych faktur w bazie.")
    except Exception as e:
        print(f"Błąd podczas szukania ostatniej faktury: {e}")