from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import SurveySubmission
import uuid
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.template.loader import render_to_string
from helpers.emails import send_cupon_email  # Replace with actual module path

class SurveySubmitAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Submit Survey",
        operation_description="Submit answers to the survey and receive a coupon if phone number is used for the first time.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["answers"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format='email'),
                "phone": openapi.Schema(type=openapi.TYPE_STRING),
                "answers": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    additional_properties=openapi.Schema(type=openapi.TYPE_STRING)
                )
            }
        ),
        responses={
            201: openapi.Response("Survey submitted successfully", openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING)
                }
            )),
            400: "Bad Request"
        }
    )
    def post(self, request):
        raw_data = request.data

        phone = raw_data.get("phone")
        name = raw_data.get("name", "")
        email = raw_data.get("email", "")
        questions_data = raw_data.get("answers", {})  # Changed from "questions"

        # ✅ DO NOT DELETE ALL SUBMISSIONS
        existing_submission = SurveySubmission.objects.filter(phone=phone).first()

        if existing_submission:
            # Second or later submission
            SurveySubmission.objects.create(
                name=name or None,
                email=email or None,
                phone=phone or None,
                coupon_code=None,
                questions=questions_data
            )
            message = "Thank you for re-taking the survey."
        else:
            # First-time submission
            coupon = f"COUPON-{uuid.uuid4().hex[:8].upper()}" if phone and email else None

            SurveySubmission.objects.create(
                name=name or None,
                email=email or None,
                phone=phone or None,
                coupon_code=coupon,
                questions=questions_data
            )

            if coupon:
                html_body = render_to_string("emails/coupon_email_template.html", {
                    "name": name,
                    "coupon": coupon
                })
                send_cupon_email(email, "Your Survey Coupon Code", html_body)
                message = f"Check your email for coupons. Your code: {coupon}"
            else:
                message = "Thank you for submitting the survey."

        return Response({"message": message}, status=status.HTTP_201_CREATED)
