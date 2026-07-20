import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.services.financial_report_service import FinancialReportService
from api.views_reports import FinancialReportView

data = FinancialReportService.generate('2026-07-01', '2026-07-31')
print("Summary:", data['summary'])

view = FinancialReportView()
excel_resp = view._generate_excel(data)
with open('test.xlsx', 'wb') as f:
    f.write(excel_resp.content)
print("Excel generated")

pdf_resp = view._generate_pdf(data)
with open('test.pdf', 'wb') as f:
    f.write(pdf_resp.content)
print("PDF generated")
