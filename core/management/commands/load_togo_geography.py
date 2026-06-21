"""
PerteDocsTG — Commande de gestion pour charger la géographie du Togo
Usage: python manage.py load_togo_geography
"""

from django.core.management.base import BaseCommand
from core.models import Region, Prefecture
from declarations.models import DocumentType


TOGO_GEOGRAPHY = {
    "Maritime": {
        "code": "MAR",
        "capital": "Lomé",
        "prefectures": [
            {"name": "Golfe", "code": "GOL", "capital": "Lomé"},
            {"name": "Agoè-Nyivé", "code": "AGO", "capital": "Agoènyivé"},
            {"name": "Vo", "code": "VO", "capital": "Vogan"},
            {"name": "Yoto", "code": "YOT", "capital": "Tabligbo"},
            {"name": "Bas-Mono", "code": "BAS", "capital": "Dévé"},
            {"name": "Lacs", "code": "LAC", "capital": "Aného"},
            {"name": "Avé", "code": "AVE", "capital": "Kévé"},
            {"name": "Zio", "code": "ZIO", "capital": "Tsévié"},
        ],
    },
    "Plateaux": {
        "code": "PLA",
        "capital": "Atakpamé",
        "prefectures": [
            {"name": "Ogou", "code": "OGO", "capital": "Atakpamé"},
            {"name": "Anié", "code": "ANI", "capital": "Anié"},
            {"name": "Est-Mono", "code": "EMO", "capital": "Elavagnon"},
            {"name": "Agou", "code": "AGU", "capital": "Agou-Nyogbo"},
            {"name": "Kloto", "code": "KLO", "capital": "Kpalimé"},
            {"name": "Danyi", "code": "DAN", "capital": "Danyi-Apéyémé"},
            {"name": "Amou", "code": "AMO", "capital": "Amlamé"},
            {"name": "Haho", "code": "HAH", "capital": "Notsé"},
            {"name": "Moyen-Mono", "code": "MMO", "capital": "Tohoun"},
            {"name": "Wawa", "code": "WAW", "capital": "Badou"},
            {"name": "Kpélé", "code": "KPE1", "capital": "Adéta"},
        ],
    },
    "Centrale": {
        "code": "CEN",
        "capital": "Sokodé",
        "prefectures": [
            {"name": "Tchaoudjo", "code": "TCHA", "capital": "Sokodé"},
            {"name": "Tchamba", "code": "TCHB", "capital": "Tchamba"},
            {"name": "Blitta", "code": "BLI", "capital": "Blitta"},
            {"name": "Sotouboua", "code": "SOT", "capital": "Sotouboua"},
            {"name": "Mô", "code": "MO", "capital": "Djarkpanga"},
        ],
    },
    "Kara": {
        "code": "KAR",
        "capital": "Kara",
        "prefectures": [
            {"name": "Kozah", "code": "KOZ", "capital": "Kara"},
            {"name": "Binah", "code": "BIN", "capital": "Pagouda"},
            {"name": "Bassar", "code": "BAS2", "capital": "Bassar"},
            {"name": "Kéran", "code": "KER", "capital": "Kanté"},
            {"name": "Assoli", "code": "ASS", "capital": "Bafilo"},
            {"name": "Dankpen", "code": "DAN2", "capital": "Guérin-Kouka"},
            {"name": "Doufelgou", "code": "DOU", "capital": "Niamtougou"},
        ],
    },
    "Savanes": {
        "code": "SAV",
        "capital": "Dapaong",
        "prefectures": [
            {"name": "Cinkassé", "code": "CIN", "capital": "Cinkassé"},
            {"name": "Tône", "code": "TON", "capital": "Dapaong"},
            {"name": "Kpendjal", "code": "KPE", "capital": "Mandouri"},
            {"name": "Kpendjal-Ouest", "code": "KPO", "capital": "Naki-Est"},
            {"name": "Tandjouaré", "code": "TAN", "capital": "Tandjouaré"},
            {"name": "Oti", "code": "OTI", "capital": "Mango"},
            {"name": "Oti-Sud", "code": "OTS", "capital": "Barkoissi"},
        ],
    },
}

DOCUMENT_TYPES = [
    {"code": "cni", "name": "Carte Nationale d'Identité", "order": 1, "processing_days": 2},
    {"code": "passeport", "name": "Passeport", "order": 2, "processing_days": 3},
    {"code": "permis_conduire", "name": "Permis de conduire", "order": 3, "processing_days": 2},
    {"code": "carte_electeur", "name": "Carte d'électeur", "order": 4, "processing_days": 2},
    {"code": "acte_naissance", "name": "Acte de naissance", "order": 5, "processing_days": 3},
    {"code": "carte_consulaire", "name": "Carte consulaire", "order": 6, "processing_days": 5},
    {"code": "carte_sejour", "name": "Carte de séjour", "order": 7, "processing_days": 5},
    {"code": "diplome", "name": "Diplôme", "order": 8, "processing_days": 3},
    {"code": "carte_grise", "name": "Carte grise", "order": 9, "processing_days": 2},
    {"code": "autre", "name": "Autre document", "order": 10, "processing_days": 5},
]


class Command(BaseCommand):
    help = "Charge les données géographiques du Togo et les types de documents"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Chargement de la géographie du Togo..."))

        region_count = 0
        prefecture_count = 0

        for region_name, region_data in TOGO_GEOGRAPHY.items():
            region, created = Region.objects.get_or_create(
                name=region_name,
                defaults={
                    "code": region_data["code"],
                    "capital": region_data["capital"],
                    "order": list(TOGO_GEOGRAPHY.keys()).index(region_name) + 1,
                },
            )
            if created:
                region_count += 1
                self.stdout.write(f"  ✓ Région : {region_name}")

            for i, pref_data in enumerate(region_data["prefectures"]):
                _, created = Prefecture.objects.get_or_create(
                    code=pref_data["code"],
                    defaults={
                        "region": region,
                        "name": pref_data["name"],
                        "capital": pref_data["capital"],
                    },
                )
                if created:
                    prefecture_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  → {region_count} régions, {prefecture_count} préfectures créées"
        ))

        self.stdout.write(self.style.NOTICE("Chargement des types de documents..."))
        doc_count = 0
        for doc_data in DOCUMENT_TYPES:
            _, created = DocumentType.objects.get_or_create(
                code=doc_data["code"],
                defaults={
                    "name": doc_data["name"],
                    "order": doc_data["order"],
                    "processing_days": doc_data["processing_days"],
                    "is_active": True,
                    "requires_number": doc_data["code"] not in ["acte_naissance", "diplome", "autre"],
                },
            )
            if created:
                doc_count += 1
                self.stdout.write(f"  ✓ Document : {doc_data['name']}")

        self.stdout.write(self.style.SUCCESS(
            f"  → {doc_count} types de documents créés"
        ))

        self.stdout.write(self.style.SUCCESS(
            "\n✅ Données géographiques chargées avec succès !"
        ))
