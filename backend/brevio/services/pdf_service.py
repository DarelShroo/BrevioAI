import pypdf

class PdfService:
    def read_pdf_in_pieces(self, path, pieces_for_page=5):
        with open(path, "rb") as archivo:
            lector = pypdf.PdfReader(archivo)
            total_paginas = len(lector.pages)

            for i in range(0, total_paginas, pieces_for_page):
                texto_parcial = ""

                for j in range(i, min(i + pieces_for_page, total_paginas)):
                    pagina = lector.pages[j]
                    texto_parcial += pagina.extract_text()
                
                yield texto_parcial
