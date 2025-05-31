from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import SurveySubmission
import uuid
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class SurveySubmitAPI(APIView):
    @swagger_auto_schema(
        operation_summary="Submit Survey",
        operation_description="Submit answers to the survey and receive a coupon if phone number is used for the first time.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["questions"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format='email'),
                "phone": openapi.Schema(type=openapi.TYPE_STRING),
                "questions": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    additional_properties=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "Qestion": openapi.Schema(type=openapi.TYPE_STRING),
                            "options": openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "text": openapi.Schema(type=openapi.TYPE_STRING),
                                        "is_selected": openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                    }
                                )
                            )
                        }
                    )
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
        questions_data = raw_data.get("questions", {})

        if phone and email:
            existing_submission = SurveySubmission.objects.filter(phone=phone).first()
        else:
            existing_submission = None

        if existing_submission:
            # Second or later submission - no coupon, save questions
            submission = SurveySubmission.objects.create(
                name=name or None,
                email=email or None,
                phone=phone or None,
                coupon_code=None,
                questions=questions_data
            )
            message = "Thank you for re-taking the survey."
        else:
            # First submission with phone+email - generate coupon
            if phone and email:
                coupon = f"COUPON-{uuid.uuid4().hex[:8].upper()}"
            else:
                coupon = None

            submission = SurveySubmission.objects.create(
                name=name or None,
                email=email or None,
                phone=phone or None,
                coupon_code=coupon,
                questions=questions_data
            )

            if coupon:
                message = f"Check your email for coupons. Your code: {coupon}"
            else:
                message = "Thank you for submitting the survey."

        return Response({"message": message}, status=status.HTTP_201_CREATED)
