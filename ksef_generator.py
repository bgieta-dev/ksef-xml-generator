import xml.etree.ElementTree as ET
from datetime import datetime
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

    def _get_nbp_rate(self, currency_code):
        if not currency_code or currency_code == 'PLN':
            return None
        try:
            url = f"https://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/?format=json"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                return Decimal(str(data['rates'][0]['mid']))
        except Exception as e:
            print(f"Błąd pobierania kursu NBP dla {currency_code}: {e}")
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
        ET.SubElement(nag, 'SystemInfo').text = 'SubiektGT-KSeF-Gen'

        p1 = ET.SubElement(root, 'Podmiot1')
        d_id1 = ET.SubElement(p1, 'DaneIdentyfikacyjne')
        ET.SubElement(d_id1, 'NIP').text = moja_firma.adr_NIP.replace('-', '')
        ET.SubElement(d_id1, 'Nazwa').text = moja_firma.adr_Nazwa
        adr1 = ET.SubElement(p1, 'Adres')
        ET.SubElement(adr1, 'KodKraju').text = moja_firma.adr_SymbolKraju if moja_firma.adr_SymbolKraju else 'PL'
        ET.SubElement(adr1, 'AdresL1').text = moja_firma.adr_Adres
        ET.SubElement(adr1, 'AdresL2').text = f"{moja_firma.adr_Kod} {moja_firma.adr_Miejscowosc}"

        p2 = ET.SubElement(root, 'Podmiot2')
        d_id2 = ET.SubElement(p2, 'DaneIdentyfikacyjne')
        country = naglowek.adr_SymbolKraju if naglowek.adr_SymbolKraju else 'PL'
        
        raw_nip = naglowek.adr_NIP.replace('-', '').replace(' ', '') if naglowek.adr_NIP else ''
        eu_countries = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'EL', 'ES', 'FI', 'FR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PT', 'RO', 'SE', 'SI', 'SK']

        if country == 'PL':
            clean_pl = raw_nip[2:] if raw_nip.upper().startswith('PL') else raw_nip
            ET.SubElement(d_id2, 'NIP').text = clean_pl
        elif country in eu_countries:
            ET.SubElement(d_id2, 'KodUE').text = country
            ET.SubElement(d_id2, 'NrVatUE').text = raw_nip
        else:
            ET.SubElement(d_id2, 'KodKraju').text = country
            ET.SubElement(d_id2, 'NrID').text = raw_nip
        
        ET.SubElement(d_id2, 'Nazwa').text = naglowek.adr_Nazwa
        adr2 = ET.SubElement(p2, 'Adres')
        ET.SubElement(adr2, 'KodKraju').text = country
        ET.SubElement(adr2, 'AdresL1').text = naglowek.adr_Adres
        ET.SubElement(adr2, 'AdresL2').text = f"{naglowek.adr_Kod} {naglowek.adr_Miejscowosc}"
        ET.SubElement(p2, 'JST').text = '2'
        ET.SubElement(p2, 'GV').text = '2'

        fa = ET.SubElement(root, 'Fa')
        currency = naglowek.dok_Waluta if naglowek.dok_Waluta else 'PLN'
        kurs_nbp = self._get_nbp_rate(currency)
        
        ET.SubElement(fa, 'KodWaluty').text = currency
        ET.SubElement(fa, 'P_1').text = datetime.now().strftime('%Y-%m-%d')
        ET.SubElement(fa, 'P_1M').text = moja_firma.adr_Miejscowosc
        ET.SubElement(fa, 'P_2').text = naglowek.dok_NrPelny
        if naglowek.dok_DataMag:
            ET.SubElement(fa, 'P_6').text = naglowek.dok_DataMag.strftime('%Y-%m-%d')

        pozycje_sorted = sorted(pozycje, key=lambda x: x.vat_Stawka if x.vat_Stawka is not None else 0, reverse=True)

        vat_summary = {}
        total_netto = Decimal('0.00')
        total_vat = Decimal('0.00')
        has_reverse_charge = False

        for poz in pozycje_sorted:
            netto = Decimal(str(poz.ob_WartNetto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            vat = Decimal(str(poz.ob_WartVat)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            stawka = int(poz.vat_Stawka) if poz.vat_Stawka is not None else 0
            vid = poz.vat_Id

            total_netto += netto
            total_vat += vat

            if vid == 100003:
                has_reverse_charge = True
                if 'oo' not in vat_summary: vat_summary['oo'] = Decimal('0.00')
                vat_summary['oo'] += netto
            else:
                if stawka not in vat_summary:
                    vat_summary[stawka] = {'netto': Decimal('0.00'), 'vat': Decimal('0.00')}
                vat_summary[stawka]['netto'] += netto
                vat_summary[stawka]['vat'] += vat

        if 23 in vat_summary:
            ET.SubElement(fa, 'P_13_1').text = f"{vat_summary[23]['netto']:.2f}"
            ET.SubElement(fa, 'P_14_1').text = f"{vat_summary[23]['vat']:.2f}"
            if kurs_nbp:
                vat_pln = (vat_summary[23]['vat'] * kurs_nbp).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                ET.SubElement(fa, 'P_14_1W').text = f"{vat_pln:.2f}"
        
        if 8 in vat_summary:
            ET.SubElement(fa, 'P_13_2').text = f"{vat_summary[8]['netto']:.2f}"
            ET.SubElement(fa, 'P_14_2').text = f"{vat_summary[8]['vat']:.2f}"
            if kurs_nbp:
                vat_pln = (vat_summary[8]['vat'] * kurs_nbp).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                ET.SubElement(fa, 'P_14_2W').text = f"{vat_pln:.2f}"

        if 5 in vat_summary:
            ET.SubElement(fa, 'P_13_3').text = f"{vat_summary[5]['netto']:.2f}"
            ET.SubElement(fa, 'P_14_3').text = f"{vat_summary[5]['vat']:.2f}"
            if kurs_nbp:
                vat_pln = (vat_summary[5]['vat'] * kurs_nbp).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                ET.SubElement(fa, 'P_14_3W').text = f"{vat_pln:.2f}"

        if has_reverse_charge:
            ET.SubElement(fa, 'P_13_5').text = f"{vat_summary['oo']:.2f}"

        if 0 in vat_summary:
            if country == 'PL':
                ET.SubElement(fa, 'P_13_6_1').text = f"{vat_summary[0]['netto']:.2f}"
            elif country in eu_countries:
                ET.SubElement(fa, 'P_13_6_2').text = f"{vat_summary[0]['netto']:.2f}"
            else:
                ET.SubElement(fa, 'P_13_6_3').text = f"{vat_summary[0]['netto']:.2f}"
        elif country != 'PL':
            if country in eu_countries:
                ET.SubElement(fa, 'P_13_6_2').text = f"{total_netto:.2f}"
            else:
                ET.SubElement(fa, 'P_13_6_3').text = f"{total_netto:.2f}"

        ET.SubElement(fa, 'P_15').text = f"{(total_netto + total_vat):.2f}"

        adn = ET.SubElement(fa, 'Adnotacje')
        ET.SubElement(adn, 'P_16').text = '1' if has_reverse_charge else '2'
        ET.SubElement(adn, 'P_17').text = '2'
        ET.SubElement(adn, 'P_18').text = '2'
        ET.SubElement(adn, 'P_18A').text = '2'
        ET.SubElement(adn, 'P_23').text = '2'

        ET.SubElement(fa, 'RodzajFaktury').text = 'VAT'

        for i, poz in enumerate(pozycje_sorted, 1):
            wiersz = ET.SubElement(fa, 'FaWiersz')
            ET.SubElement(wiersz, 'NrWierszaFa').text = str(i)
            ET.SubElement(wiersz, 'UU_ID').text = str(uuid.uuid4())
            ET.SubElement(wiersz, 'P_7').text = poz.tw_Nazwa if poz.tw_Nazwa else 'Towar/Usługa'
            ET.SubElement(wiersz, 'P_8A').text = poz.ob_Jm
            ET.SubElement(wiersz, 'P_8B').text = f"{Decimal(str(poz.ob_Ilosc)):.2f}"
            
            netto = Decimal(str(poz.ob_WartNetto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            ilosc = Decimal(str(poz.ob_Ilosc))
            cena_jednostkowa = (netto / ilosc).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP) if ilosc != 0 else Decimal('0.00')
            
            ET.SubElement(wiersz, 'P_9A').text = f"{cena_jednostkowa:.2f}"
            ET.SubElement(wiersz, 'P_11').text = f"{netto:.2f}"
            
            # Rate determination logic
            stawka = poz.vat_Stawka
            vid = poz.vat_Id
            
            if vid == 100003:
                rate_text = "oo"
            elif stawka is not None and stawka > 0:
                rate_text = f"{stawka:.0f}"
            else:
                # 0% or None
                if country == 'PL':
                    rate_text = "0 KR"
                elif country in eu_countries:
                    rate_text = "0 WDT"
                else:
                    rate_text = "0 EX"
                    
            ET.SubElement(wiersz, 'P_12').text = rate_text
            
            if kurs_nbp:
                ET.SubElement(wiersz, 'KursWaluty').text = f"{kurs_nbp:.4f}"

        raw_xml = ET.tostring(root, encoding='utf-8')
        parsed = minidom.parseString(raw_xml)
        return parsed.toprettyxml(indent="  ", encoding="utf-8")

    def save(self, xml_content, filename):
        with open(filename, 'wb') as f:
            f.write(xml_content)
        print(f"Zapisano plik: {filename}")
