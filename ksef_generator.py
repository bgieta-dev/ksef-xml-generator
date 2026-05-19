import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import xml.dom.minidom as minidom
import uuid
from decimal import Decimal, ROUND_HALF_UP
import urllib.request
import json

class KsefGenerator:
    def __init__(self):
        self.ns = {
            '': 'http://crd.gov.pl/wzor/2025/06/25/13775/',
            'etd': 'http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/01/05/eD/DefinicjeTypy/',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
        for prefix, uri in self.ns.items():
            ET.register_namespace(prefix, uri)

    def _get_nbp_rate(self, currency_code, date_to_check):
        if not currency_code or currency_code == 'PLN':
            return None
        
        # Kurs waluty bierzemy z ostatniego dnia roboczego POPRZEDZAJĄCEGO datę wystawienia
        # Szukamy max 10 dni wstecz (na wypadek długich świąt)
        check_date = date_to_check - timedelta(days=1)
        
        for _ in range(10):
            date_str = check_date.strftime('%Y-%m-%d')
            try:
                url = f"https://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/{date_str}/?format=json"
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    return Decimal(str(data['rates'][0]['mid']))
            except Exception:
                # Jeśli 404 (brak tabeli dla tego dnia), szukamy dzień wcześniej
                check_date -= timedelta(days=1)
                continue
        
        print(f"Nie znaleziono kursu NBP dla {currency_code} w okolicy {date_to_check}")
        return None

    def generate(self, moja_firma, naglowek, tabela_vat, pozycje):
        root = ET.Element('Faktura', {
            'xmlns': self.ns[''],
            'xmlns:etd': self.ns['etd'],
            'xmlns:xsi': self.ns['xsi']
        })

        nag = ET.SubElement(root, 'Naglowek')
        ET.SubElement(nag, 'KodFormularza', {
            'kodSystemowy': 'FA (3)',
            'wersjaSchemy': '1-0E'
        }).text = 'FA'
        ET.SubElement(nag, 'WariantFormularza').text = '3'
        ET.SubElement(nag, 'DataWytworzeniaFa').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        ET.SubElement(nag, 'SystemInfo').text = 'Bgieta-Ksef-Gen'

        p1 = ET.SubElement(root, 'Podmiot1')
        d_id1 = ET.SubElement(p1, 'DaneIdentyfikacyjne')
        ET.SubElement(d_id1, 'NIP').text = moja_firma.adr_NIP.replace('-', '').replace(' ', '')
        
        # Nazwa musi być PO NIP w FA(3)
        nazwa_sprzedawcy = moja_firma.adr_NazwaPelna if hasattr(moja_firma, 'adr_NazwaPelna') and moja_firma.adr_NazwaPelna else moja_firma.adr_Nazwa
        ET.SubElement(d_id1, 'Nazwa').text = nazwa_sprzedawcy
        
        adr1 = ET.SubElement(p1, 'Adres')
        ET.SubElement(adr1, 'KodKraju').text = moja_firma.adr_SymbolKraju if moja_firma.adr_SymbolKraju else 'PL'
        ET.SubElement(adr1, 'AdresL1').text = moja_firma.adr_Adres
        ET.SubElement(adr1, 'AdresL2').text = f"{moja_firma.adr_Kod} {moja_firma.adr_Miejscowosc}"

        p2 = ET.SubElement(root, 'Podmiot2')
        d_id2 = ET.SubElement(p2, 'DaneIdentyfikacyjne')
        
        raw_nip = naglowek.adr_NIP.replace('-', '').replace(' ', '') if naglowek.adr_NIP else ''
        eu_countries = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'EL', 'ES', 'FI', 'FR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PT', 'RO', 'SE', 'SI', 'SK']
        
        detected_country = naglowek.adr_SymbolKraju if naglowek.adr_SymbolKraju else 'PL'
        if len(raw_nip) > 2 and raw_nip[:2].isalpha():
            prefix = raw_nip[:2].upper()
            if prefix in eu_countries or prefix == 'PL':
                detected_country = prefix
                raw_nip = raw_nip[2:]
            elif prefix != 'PL':
                detected_country = prefix
                raw_nip = raw_nip[2:]

        country = detected_country

        # W FA(3) NIP/KodUE musi być PRZED Nazwą
        if country == 'PL':
            ET.SubElement(d_id2, 'NIP').text = raw_nip
        elif country in eu_countries:
            ET.SubElement(d_id2, 'KodUE').text = country
            ET.SubElement(d_id2, 'NrVatUE').text = raw_nip
        else:
            ET.SubElement(d_id2, 'KodKraju').text = country
            ET.SubElement(d_id2, 'NrID').text = raw_nip

        # Nazwa nabywcy po identyfikatorach
        nazwa_nabywcy = naglowek.adr_NazwaPelna if hasattr(naglowek, 'adr_NazwaPelna') and naglowek.adr_NazwaPelna else naglowek.adr_Nazwa
        ET.SubElement(d_id2, 'Nazwa').text = nazwa_nabywcy
        
        adr2 = ET.SubElement(p2, 'Adres')
        ET.SubElement(adr2, 'KodKraju').text = country
        ET.SubElement(adr2, 'AdresL1').text = naglowek.adr_Adres
        ET.SubElement(adr2, 'AdresL2').text = f"{naglowek.adr_Kod} {naglowek.adr_Miejscowosc}"
        ET.SubElement(p2, 'JST').text = '2'
        ET.SubElement(p2, 'GV').text = '2'

        fa = ET.SubElement(root, 'Fa')
        currency = naglowek.dok_Waluta if naglowek.dok_Waluta else 'PLN'
        
        # Data wystawienia z dokumentu
        data_wystawienia_orig = naglowek.dok_DataWyst if naglowek.dok_DataWyst else today
        data_wystawienia_str = data_wystawienia_orig.strftime('%Y-%m-%d')
        
        # Data sprzedaży
        data_sprzedazy = naglowek.dok_DataMag if naglowek.dok_DataMag else data_wystawienia_orig

        # Kurs waluty bierzemy z ostatniego dnia roboczego przed WCZEŚNIEJSZĄ z dat pierwotnych
        data_do_kursu = data_wystawienia_orig if data_wystawienia_orig < data_sprzedazy else data_sprzedazy

        # Kurs dokumentu (bazy) - przeliczamy z PLN na Walutę
        kurs_dok = Decimal(str(naglowek.dok_WalutaKurs)) if naglowek.dok_WalutaKurs and currency != 'PLN' else Decimal('1.00')
        jednostka_wal = Decimal(str(naglowek.dok_WalutaLiczbaJednostek)) if hasattr(naglowek, 'dok_WalutaLiczbaJednostek') and naglowek.dok_WalutaLiczbaJednostek else Decimal('1.0')
        
        # Realny kurs do obliczeń (kurs / liczba jednostek)
        efektywny_kurs = (kurs_dok / jednostka_wal) if kurs_dok != 0 else Decimal('1.00')

        # Pobieramy kurs NBP z dnia roboczego przed datą zdarzenia - tag KursWaluty (informacyjnie)
        kurs_nbp = self._get_nbp_rate(currency, data_do_kursu)
        
        ET.SubElement(fa, 'KodWaluty').text = currency
        ET.SubElement(fa, 'P_1').text = data_wystawienia_str
        ET.SubElement(fa, 'P_1M').text = moja_firma.adr_Miejscowosc
        ET.SubElement(fa, 'P_2').text = naglowek.dok_NrPelny.replace('Sprzedaż ', 'FS ') if naglowek.dok_NrPelny else ''
        if naglowek.dok_DataMag:
            ET.SubElement(fa, 'P_6').text = naglowek.dok_DataMag.strftime('%Y-%m-%d')

        pozycje_sorted = sorted(pozycje, key=lambda x: x.vat_Stawka if x.vat_Stawka is not None else 0, reverse=True)

        vat_summary = {}
        total_netto_wal = Decimal('0.00')
        total_vat_wal = Decimal('0.00')
        has_reverse_charge = False
        has_reverse_charge = False
        has_wdt = False
        has_export = False
        
        for poz in pozycje_sorted:
            # Mapowanie stawek VAT z Subiekta na KSeF
            try:
                # tw_Rodzaj: 1=Towar, 2=Usługa
                rodzaj = poz.tw_Rodzaj if hasattr(poz, 'tw_Rodzaj') else 1
                
                if poz.vat_Stawka is not None:
                    val = float(poz.vat_Stawka)
                    if val == 0:
                        if rodzaj == 2:
                            # Eksport usług / OO
                            st_vat = "oo"
                            has_reverse_charge = True
                        elif country == 'PL':
                            # OO krajowe
                            st_vat = "oo"
                            has_reverse_charge = True
                        elif country in eu_countries:
                            # WDT (FA3: P_13_6_2)
                            st_vat = "wdt"
                            has_wdt = True
                        else:
                            # Eksport towarów (FA3: P_13_6_3)
                            st_vat = "export"
                            has_export = True
                    else:
                        st_vat = str(int(val))
                else:
                    st_vat = "oo"
                    has_reverse_charge = True
            except:
                st_vat = "np"

            if st_vat not in vat_summary:
                vat_summary[st_vat] = {
                    'netto_pln': Decimal('0.00'),
                    'vat_pln': Decimal('0.00'),
                    'netto_wal': Decimal('0.00'),
                    'vat_wal': Decimal('0.00')
                }
            
            # Wartości w bazie Subiekta są ZAWSZE w PLN
            netto_pln = Decimal(str(poz.ob_WartNetto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            vat_pln = Decimal(str(poz.ob_WartVat)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Przeliczamy na Walutę (PLN / kurs)
            if currency != 'PLN' and efektywny_kurs != 0:
                netto_wal = (netto_pln / efektywny_kurs).quantize(Decimal('0.02'), rounding=ROUND_HALF_UP)
                vat_wal = (vat_pln / efektywny_kurs).quantize(Decimal('0.02'), rounding=ROUND_HALF_UP)
            else:
                netto_wal = netto_pln
                vat_wal = vat_pln
            
            vat_summary[st_vat]['netto_pln'] += netto_pln
            vat_summary[st_vat]['vat_pln'] += vat_pln
            vat_summary[st_vat]['netto_wal'] += netto_wal
            vat_summary[st_vat]['vat_wal'] += vat_wal
            
            total_netto_wal += netto_wal
            total_vat_wal += vat_wal

        # Sekcje sumaryczne VAT (P_13, P_14, P_15) w walucie faktury
        # Mapowanie stawek FA(3)
        
        # 23% / 22%
        if '23' in vat_summary or '22' in vat_summary:
            s = vat_summary.get('23', vat_summary.get('22'))
            ET.SubElement(fa, 'P_13_1').text = f"{s['netto_wal']:.2f}"
            ET.SubElement(fa, 'P_14_1').text = f"{s['vat_wal']:.2f}"
            if currency != 'PLN':
                ET.SubElement(fa, 'P_14_1W').text = f"{s['vat_pln']:.2f}"
        
        # 8% / 7%
        if '8' in vat_summary or '7' in vat_summary:
            s = vat_summary.get('8', vat_summary.get('7'))
            ET.SubElement(fa, 'P_13_2').text = f"{s['netto_wal']:.2f}"
            ET.SubElement(fa, 'P_14_2').text = f"{s['vat_wal']:.2f}"
            if currency != 'PLN':
                ET.SubElement(fa, 'P_14_2W').text = f"{s['vat_pln']:.2f}"
            
        # 5%
        if '5' in vat_summary:
            s = vat_summary['5']
            ET.SubElement(fa, 'P_13_3').text = f"{s['netto_wal']:.2f}"
            ET.SubElement(fa, 'P_14_3').text = f"{s['vat_wal']:.2f}"
            if currency != 'PLN':
                ET.SubElement(fa, 'P_14_3W').text = f"{s['vat_pln']:.2f}"

        # 0% Krajowe (P_13_5)
        if '0' in vat_summary:
            ET.SubElement(fa, 'P_13_5').text = f"{vat_summary['0']['netto_wal']:.2f}"

        # WDT (FA3: P_13_6_2)
        if 'wdt' in vat_summary:
            ET.SubElement(fa, 'P_13_6_2').text = f"{vat_summary['wdt']['netto_wal']:.2f}"

        # Export (FA3: P_13_6_3)
        if 'export' in vat_summary:
            ET.SubElement(fa, 'P_13_6_3').text = f"{vat_summary['export']['netto_wal']:.2f}"

        # zw (Zwolnione)
        if 'zw' in vat_summary:
            ET.SubElement(fa, 'P_13_6').text = f"{vat_summary['zw']['netto_wal']:.2f}"
            
        # np / oo (Nie podlegające / Odwrotne Obciążenie / Eksport usług)
        if 'np' in vat_summary or 'oo' in vat_summary:
            total_np_oo = Decimal('0.00')
            if 'np' in vat_summary:
                total_np_oo += vat_summary['np']['netto_wal']
            if 'oo' in vat_summary:
                total_np_oo += vat_summary['oo']['netto_wal']
            ET.SubElement(fa, 'P_13_7').text = f"{total_np_oo:.2f}"

        # Suma brutto (P_15) w walucie faktury
        total_brutto_wal = sum(v['netto_wal'] for v in vat_summary.values()) + sum(v['vat_wal'] for v in vat_summary.values())
        ET.SubElement(fa, 'P_15').text = f"{total_brutto_wal:.2f}"
        
        # Sekcja Adnotacje (wymagana w FA(3))
        adnotacje = ET.SubElement(fa, 'Adnotacje')
        ET.SubElement(adnotacje, 'P_16').text = '2'
        ET.SubElement(adnotacje, 'P_17').text = '2'
        ET.SubElement(adnotacje, 'P_18').text = '1' if has_reverse_charge else '2'
        ET.SubElement(adnotacje, 'P_18A').text = '2'
        
        zwolnienie = ET.SubElement(adnotacje, 'Zwolnienie')
        ET.SubElement(zwolnienie, 'P_19N').text = '1'
        
        nst = ET.SubElement(adnotacje, 'NoweSrodkiTransportu')
        ET.SubElement(nst, 'P_22N').text = '1'
        
        ET.SubElement(adnotacje, 'P_23').text = '2'
        
        pmarzy = ET.SubElement(adnotacje, 'PMarzy')
        ET.SubElement(pmarzy, 'P_PMarzyN').text = '1'

        ET.SubElement(fa, 'RodzajFaktury').text = 'VAT'

        # Dane pozycji (FaWiersz)
        nr_poz = 1
        for poz in pozycje:
            wiersz = ET.SubElement(fa, 'FaWiersz')
            ET.SubElement(wiersz, 'NrWierszaFa').text = str(nr_poz)
            
            # UU_ID jest wymagane w FA(3)
            ET.SubElement(wiersz, 'UU_ID').text = uuid.uuid4().hex[:16]

            ET.SubElement(wiersz, 'P_7').text = poz.tw_Nazwa if poz.tw_Nazwa else 'Towar/Usługa'
            ET.SubElement(wiersz, 'P_8A').text = poz.ob_Jm if poz.ob_Jm else 'szt'
            ET.SubElement(wiersz, 'P_8B').text = f"{poz.ob_Ilosc:.3f}"
            
            # Wartości w walucie faktury (P_9A, P_11)
            # Wyliczamy cenę jednostkową walutową (Wartość walutowa / Ilość)
            netto_pln_poz = Decimal(str(poz.ob_WartNetto))
            netto_wal_poz = (netto_pln_poz / efektywny_kurs).quantize(Decimal('0.02'), rounding=ROUND_HALF_UP) if efektywny_kurs != 0 else netto_pln_poz
            
            cena_wal_poz = (netto_wal_poz / Decimal(str(poz.ob_Ilosc))).quantize(Decimal('0.02'), rounding=ROUND_HALF_UP) if poz.ob_Ilosc != 0 else netto_wal_poz
            
            ET.SubElement(wiersz, 'P_9A').text = f"{cena_wal_poz:.2f}"
            ET.SubElement(wiersz, 'P_11').text = f"{netto_wal_poz:.2f}"
            
            # W FA(3) dla OO P_12 powinno być zgodne ze stawką (np. 'oo' lub 'np')
            # Ale jeśli to jest OO, to raportujemy st_vat (które jest 'oo' lub 'np' lub numerem)
            # Stawka 0% dla WDT/Export musi być raportowana jako "0"
            
            # Ponownie przeliczamy st_vat dla konkretnego wiersza
            try:
                rodzaj_poz = poz.tw_Rodzaj if hasattr(poz, 'tw_Rodzaj') else 1
                if poz.vat_Stawka is not None:
                    val = float(poz.vat_Stawka)
                    if val == 0:
                        if rodzaj_poz == 2 or country == "PL":
                            st_vat_poz = "oo"
                        elif country in eu_countries:
                            st_vat_poz = "0 WDT"
                        else:
                            st_vat_poz = "0 EX"
                    else:
                        st_vat_poz = str(int(val))
                else:
                    st_vat_poz = "oo"
            except:
                st_vat_poz = "np"

            ET.SubElement(wiersz, 'P_12').text = st_vat_poz
            
            # Kurs NBP w tagu KursWaluty (informacyjnie, pobierany z internetu)
            if currency != 'PLN' and kurs_nbp:
                ET.SubElement(wiersz, 'KursWaluty').text = f"{kurs_nbp:.4f}"
            
            nr_poz += 1

        # Suma faktury w walucie (opcjonalnie w stopce lub tagach walutowych)
        if currency != 'PLN':
            # KSeF FA(3) wymaga sumy VAT w PLN (P_14), ale można dodać adnotację o walucie
            pass

        return root

    def save(self, root, filename):
        xml_str = ET.tostring(root, encoding='utf-8')
        parsed_xml = minidom.parseString(xml_str)
        pretty_xml = parsed_xml.toprettyxml(indent="  ", encoding='utf-8')
        
        with open(filename, 'wb') as f:
            f.write(pretty_xml)
