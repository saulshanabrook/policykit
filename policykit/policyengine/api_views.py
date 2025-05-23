from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound 
from django.contrib.auth import get_user
from django.db import transaction
from silk.profiling.profiler import silk_profile
from policyengine.serializers import MembersSerializer, PutMembersRequestSerializer, CommunityDashboardSerializer

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def members(request):
    user = get_user(request)

    if request.method == 'GET':
        return Response(MembersSerializer(user.community.community).data)


    if request.method == 'PUT':
        req = PutMembersRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        put_members(user, **req.validated_data)
        return Response({}, status=200)

    raise NotImplementedError

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@silk_profile()
def dashboard(request):
    user = get_user(request)
    return Response(CommunityDashboardSerializer(user.community.community).data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def community_doc(request):
    user = get_user(request)
    community = user.community.community
    text = request.data['text']
    name = request.data['name']
    doc = community.get_documents()[0]
    if text is not None:
        doc.text = text
    if name is not None:
        doc.name = name
    doc.save()
    return Response({}, status=200)



def put_members(user, action, role, members):
    from constitution.models import (PolicykitAddUserRole,
                                     PolicykitRemoveUserRole)

    from policyengine.models import CommunityRole, CommunityUser

    action_model = None
    if action == 'Add':
        action_model = PolicykitAddUserRole()
    elif action == 'Remove':
        action_model = PolicykitRemoveUserRole()
    else:
        raise ValueError('Invalid action')

    action_model.community = user.constitution_community
    action_model.initiator = user
    try:
        action_model.role = CommunityRole.objects.filter(pk=role, community=user.community.community)[0]
    except IndexError:
        raise NotFound('Role not found')

    action_model.save(evaluate_action=False)
    action_model.users.set(CommunityUser.objects.filter(id__in=members, community__community=user.community.community))
    if len(action_model.users.all()) != len(members):
        raise NotFound('User not found')
    action_model.save(evaluate_action=True)

