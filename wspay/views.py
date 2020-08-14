from django.views.generic import FormView, View
from django.http import HttpResponse
from django.shortcuts import render, redirect


from wspay.forms import UnprocessedPaymentForm, WSPaySignedForm
from wspay.services import process_data, generate_signature
from wspay.conf import settings


class ProcessView(FormView):
    """Receive payment data and prepare it for WSPay."""

    def form_valid(self, form):
        form_data = process_data(form.cleaned_data)
        wspay_form = WSPaySignedForm(form_data)
        return render(
            self.request,
            'wspay/wspaypost.html',
            {'form': wspay_form, 'url': settings.PAYMENT_ENDPOINT}
        )


class PaymentStatus:
    SUCCESS = 'success'
    ERROR = 'error'
    CANCEL = 'cancel'


class ProcessResponseView(View):
    """Handle success, error and cancel."""

    def dispatch(self, request, *args, **kwargs):
        status = kwargs['status']
        assert status in [PaymentStatus.SUCCESS, PaymentStatus.ERROR, PaymentStatus.CANCEL]
        if(status == PaymentStatus.SUCCESS):
            try:
                data = {
                    'ShoppingCartID': int(request.GET.get('ShoppingCartID')),
                    'Success': int(request.GET.get('Success')),
                    'ApprovalCode': request.GET.get('ApprovalCode'),
                    'Signature': request.GET.get('Signature'),
                }
            except Exception:
                return redirect('wspay:failed')

            param_list = [
                settings.SHOP_ID,
                data['ShoppingCartID'],
                data['Success'],
                data['ApprovalCode']
            ]
            sig = generate_signature(param_list)
            if(data['Success'] != 1 or data['ApprovalCode'] == '' or data['Signature'] != sig):
                return redirect('wspay:failed')

        elif(status == PaymentStatus.CANCEL):
            return HttpResponse('Transaction was canceled!')
        else:
            return HttpResponse('An error occurred!')


class TestView(FormView):
    """Simple View to test the ProcessView."""

    template_name = 'wspay/test.html'
    form_class = UnprocessedPaymentForm


class FailedView(View):
    """Handle failed transactions."""

    def get(self, request, *args, **kwargs):
        return HttpResponse('Transaction failed!')
