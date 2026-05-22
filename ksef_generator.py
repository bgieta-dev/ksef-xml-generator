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
        check_date = date_to_check - timedelta(days=1)
        for _ in range(10):
            date_str = check_date.strftime('%Y-%m-%d')
            try:
                url = f"https://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/{date_str}/?format=json"
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    return Decimal(str(data['rates'][0]['mid']))
            except Exception:
                check_date -= timedelta(days=1)
                continue
        return None

    def _get_val(self, obj, key, index, default=None):
        """Pomocnicza funkcja do pobierania danych z dict lub tuple/pyodbc.Row"""
        if isinstance(obj, dict):
            return obj.get(key, default)
        try:
            return getattr(obj, key)
        except AttributeError:
            try:
                return obj[index]
            except (IndexError, TypeError):
                return default

    def generate(self, moja_firma, naglowek, tabela_vat, pozycje):
        root = ET.Element('Faktura', {
            'xmlns': self.ns[''],
            'xmlns:etd': self.ns['etd'],
            'xmlns:xsi': self.ns['xsi']
        })

        nag = ET.SubElement(root, 'Naglowek')
        ET.SubElement(nag, 'KodFormularza', {'kodSystemowy': 'FA (3)', 'wersjaSchemy': '1-0E'}).text = 'FA'
        ET.SubElement(nag, 'WariantFormularza').text = '3'
        ET.SubElement(nag, 'DataWytworzeniaFa').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        ET.SubElement(nag, 'SystemInfo').text = 'Bgieta-Ksef-Gen'

        # Dane Sprzedawcy
        p1 = ET.SubElement(root, 'Podmiot1')
        d_id1 = ET.SubElement(p1, 'DaneIdentyfikacyjne')
        nip_1 = str(self._get_val(moja_firma, 'adr_NIP', 2, '')).replace('-', '').replace(' ', '')
        ET.SubElement(d_id1, 'NIP').text = nip_1
        nazwa_1 = self._get_val(moja_firma, 'adr_NazwaPelna', 0) or self._get_val(moja_firma, 'adr_Nazwa', 1)
        ET.SubElement(d_id1, 'Nazwa').text = str(nazwa_1)
        
        adr1 = ET.SubElement(p1, 'Adres')
        ET.SubElement(adr1, 'KodKraju').text = self._get_val(moja_firma, 'adr_SymbolKraju', 6, 'PL')
        ET.SubElement(adr1, 'AdresL1').text = self._get_val(moja_firma, 'adr_Adres', 4)
        ET.SubElement(adr1, 'AdresL2').text = f"{self._get_val(moja_firma, 'adr_Kod', 5)} {self._get_val(moja_firma, 'adr_Miejscowosc', 3)}"

        # Dane Nabywcy
        p2 = ET.SubElement(root, 'Podmiot2')
        d_id2 = ET.SubElement(p2, 'DaneIdentyfikacyjne')
        
        raw_nip = str(self._get_val(naglowek, 'adr_NIP', 5, '')).replace('-', '').replace(' ', '')
        eu_countries = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'EL', 'ES', 'FI', 'FR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PT', 'RO', 'SE', 'SI', 'SK']
        country = self._get_val(naglowek, 'adr_SymbolKraju', 9, 'PL')
        
        if len(raw_nip) > 2 and raw_nip[:2].isalpha():
            prefix = raw_nip[:2].upper()
            if prefix in eu_countries or prefix == 'PL':
                country = prefix
                raw_nip = raw_nip[2:]

        if country == 'PL':
            ET.SubElement(d_id2, 'NIP').text = raw_nip
        elif country in eu_countries:
            ET.SubElement(d_id2, 'KodUE').text = country
            ET.SubElement(d_id2, 'NrVatUE').text = raw_nip
        else:
            ET.SubElement(d_id2, 'KodKraju').text = country
            ET.SubElement(d_id2, 'NrID').text = raw_nip

        nazwa_2 = self._get_val(naglowek, 'adr_NazwaPelna', 4) or self._get_val(naglowek, 'adr_Nazwa', 5)
        ET.SubElement(d_id2, 'Nazwa').text = str(nazwa_2)
        
        adr2 = ET.SubElement(p2, 'Adres')
        ET.SubElement(adr2, 'KodKraju').text = country
        ET.SubElement(adr2, 'AdresL1').text = self._get_val(naglowek, 'adr_Adres', 7)
        ET.SubElement(adr2, 'AdresL2').text = f"{self._get_val(naglowek, 'adr_Kod', 8)} {self._get_val(naglowek, 'adr_Miejscowosc', 6)}"
        ET.SubElement(p2, 'JST').text = '2'
        ET.SubElement(p2, 'GV').text = '2'

        # Sekcja Fa
        fa = ET.SubElement(root, 'Fa')
        currency = self._get_val(naglowek, 'dok_Waluta', 18, 'PLN')
        data_wyst = self._get_val(naglowek, 'dok_DataWyst', 2)
        data_sprz = self._get_val(naglowek, 'dok_DataMag', 3) or data_wyst
        
        kurs_dok = Decimal(str(self._get_val(naglowek, 'dok_WalutaKurs', 19, '1.0'))) if currency != 'PLN' else Decimal('1.0')
        kurs_nbp = self._get_nbp_rate(currency, data_wyst if data_wyst < data_sprz else data_sprz)
        
        ET.SubElement(fa, 'KodWaluty').text = currency
        ET.SubElement(fa, 'P_1').text = data_wyst.strftime('%Y-%m-%d')
        ET.SubElement(fa, 'P_1M').text = self._get_val(moja_firma, 'adr_Miejscowosc', 3)
        nr_pelny = self._get_val(naglowek, 'dok_NrPelny', 1)
        ET.SubElement(fa, 'P_2').text = str(nr_pelny).replace('Sprzedaż ', 'FS ')
        ET.SubElement(fa, 'P_6').text = data_sprz.strftime('%Y-%m-%d')

        # Procesowanie pozycji
        vat_summary = {}
        has_reverse_charge = False
        
        # Sortowanie z odpornością na typ danych
        pozycje_list = list(pozycje)
        pozycje_list.sort(key=lambda x: float(self._get_val(x, 'vat_Stawka', 8, 0) or 0), reverse=True)

        for poz in pozycje_list:
            rodzaj = self._get_val(poz, 'tw_Rodzaj', 10, 1) or 1
            symbol = str(self._get_val(poz, 'vat_Symbol', 9, '')).lower()
            nazwa = str(self._get_val(poz, 'tw_Nazwa', 0, '')).lower()
            stawka_val = self._get_val(poz, 'vat_Stawka', 8)
            
            is_svc = (rodzaj == 2) or ("transport" in nazwa) or ("shipping" in nazwa)
            
            st_vat = "np_oo"
            if stawka_val is not None:
                val = float(stawka_val)
                if val == 0 or symbol == 'np':
                    if is_svc or symbol == 'np':
                        st_vat = "np_oo"
                        has_reverse_charge = True
                    elif country == 'PL': st_vat = "0_kraj"
                    elif country in eu_countries: st_vat = "wdt"
                    else: st_vat = "export"
                elif symbol == 'zw': st_vat = "zw"
                else: st_vat = str(int(val))
            else:
                st_vat = "np_oo"
                has_reverse_charge = True

            if st_vat not in vat_summary:
                vat_summary[st_vat] = {'n_pln': Decimal('0'), 'v_pln': Decimal('0'), 'n_wal': Decimal('0'), 'v_wal': Decimal('0')}
            
            n_p = Decimal(str(self._get_val(poz, 'ob_WartNetto', 4))).quantize(Decimal('0.01'), ROUND_HALF_UP)
            v_p = Decimal(str(self._get_val(poz, 'ob_WartVat', 5))).quantize(Decimal('0.01'), ROUND_HALF_UP)
            
            vat_summary[st_vat]['n_pln'] += n_p
            vat_summary[st_vat]['v_pln'] += v_p
            vat_summary[st_vat]['n_wal'] += (n_p / kurs_dok).quantize(Decimal('0.02'), ROUND_HALF_UP)
            vat_summary[st_vat]['v_wal'] += (v_p / kurs_dok).quantize(Decimal('0.02'), ROUND_HALF_UP)

        # Mapowanie pól P_13/P_14
        mappings = {'23': '1', '8': '2', '5': '3'}
        for rate, suffix in mappings.items():
            if rate in vat_summary:
                s = vat_summary[rate]
                ET.SubElement(fa, f'P_13_{suffix}').text = f"{s['n_wal']:.2f}"
                ET.SubElement(fa, f'P_14_{suffix}').text = f"{s['v_wal']:.2f}"
                if currency != 'PLN': ET.SubElement(fa, f'P_14_{suffix}W').text = f"{s['v_pln']:.2f}"

        if '0_kraj' in vat_summary: ET.SubElement(fa, 'P_13_4').text = f"{vat_summary['0_kraj']['n_wal']:.2f}"
        if 'np_oo' in vat_summary: ET.SubElement(fa, 'P_13_5').text = f"{vat_summary['np_oo']['n_wal']:.2f}"
        if 'wdt' in vat_summary: ET.SubElement(fa, 'P_13_6_2').text = f"{vat_summary['wdt']['n_wal']:.2f}"
        if 'export' in vat_summary: ET.SubElement(fa, 'P_13_6_3').text = f"{vat_summary['export']['n_wal']:.2f}"
        if 'zw' in vat_summary: ET.SubElement(fa, 'P_13_7').text = f"{vat_summary['zw']['n_wal']:.2f}"

        total_brutto = sum(v['n_wal'] for v in vat_summary.values()) + sum(v['v_wal'] for v in vat_summary.values())
        ET.SubElement(fa, 'P_15').text = f"{total_brutto:.2f}"
        
        ad = ET.SubElement(fa, 'Adnotacje')
        ET.SubElement(ad, 'P_16').text = '2'
        ET.SubElement(ad, 'P_17').text = '2'
        ET.SubElement(ad, 'P_18').text = '2'
        ET.SubElement(ad, 'P_18A').text = '1' if has_reverse_charge else '2'
        ET.SubElement(ET.SubElement(ad, 'Zwolnienie'), 'P_19N').text = '1'
        ET.SubElement(ET.SubElement(ad, 'NoweSrodkiTransportu'), 'P_22N').text = '1'
        ET.SubElement(ad, 'P_23').text = '2'
        ET.SubElement(ET.SubElement(ad, 'PMarzy'), 'P_PMarzyN').text = '1'
        ET.SubElement(fa, 'RodzajFaktury').text = 'VAT'

        for i, poz in enumerate(pozycje, 1):
            w = ET.SubElement(fa, 'FaWiersz')
            ET.SubElement(w, 'NrWierszaFa').text = str(i)
            ET.SubElement(w, 'UU_ID').text = uuid.uuid4().hex[:16]
            ET.SubElement(w, 'P_7').text = self._get_val(poz, 'tw_Nazwa', 0, 'Usługa')
            ET.SubElement(w, 'P_8A').text = self._get_val(poz, 'ob_Jm', 2, 'szt')
            ET.SubElement(w, 'P_8B').text = f"{float(self._get_val(poz, 'ob_Ilosc', 1)):.3f}"
            
            n_w = (Decimal(str(self._get_val(poz, 'ob_WartNetto', 4))) / kurs_dok).quantize(Decimal('0.02'), ROUND_HALF_UP)
            p_w = (n_w / Decimal(str(self._get_val(poz, 'ob_Ilosc', 1)))).quantize(Decimal('0.02'), ROUND_HALF_UP) if float(self._get_val(poz, 'ob_Ilosc', 1)) != 0 else n_w
            ET.SubElement(w, 'P_9A').text = f"{p_w:.2f}"
            ET.SubElement(w, 'P_11').text = f"{n_w:.2f}"
            
            # P_12 Logic
            r_p = self._get_val(poz, 'tw_Rodzaj', 10, 1) or 1
            s_p = str(self._get_val(poz, 'vat_Symbol', 9, '')).lower()
            n_p = str(self._get_val(poz, 'tw_Nazwa', 0, '')).lower()
            is_s = (r_p == 2) or ("transport" in n_p) or ("shipping" in n_p)
            st_p = "oo" if (is_s or s_p == 'np') else "0"
            if self._get_val(poz, 'vat_Stawka', 8) is not None:
                v_p = float(self._get_val(poz, 'vat_Stawka', 8))
                if v_p == 0 or s_p == 'np':
                    if is_s or s_p == 'np': st_p = "oo"
                    elif country == 'PL': st_p = "0"
                    elif country in eu_countries: st_p = "0 WDT"
                    else: st_p = "0 EX"
                elif s_p == 'zw': st_p = "zw"
                else: st_p = str(int(v_p))
            
            ET.SubElement(w, 'P_12').text = st_p
            if currency != 'PLN' and kurs_nbp: ET.SubElement(w, 'KursWaluty').text = f"{kurs_nbp:.4f}"

        return root

    def save(self, root, filename):
        xml_str = ET.tostring(root, encoding='utf-8')
        pretty = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding='utf-8')
        with open(filename, 'wb') as f: f.write(pretty)
