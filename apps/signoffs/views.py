"""Collective Executive Sign-Off & Term Succession (Phase 6).

Protocol:
1. Preparation: Outgoing officers submit Handover Notes and set up Next A.Y. Plan.
2. Initiation: An Executive opens sign-off, setting Term.status = PENDING_SIGNOFF.
3. Consensus: Every active Executive reviews transition records and casts a vote (APPROVED or CHANGES_REQUESTED).
4. If CHANGES_REQUESTED: Term reverts to ACTIVE, prior votes clear, and officers are notified to revise.
5. Unanimous APPROVAL: The current term is CLOSED, the planned Term is activated as the new ACTIVE term,
   and executive leadership rolls over smoothly.
"""
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import (
    HandoverNote,
    Membership,
    Term,
    TermPlan,
    TermSignOff,
)
from apps.shared.notify import notify
from apps.shared.permissions import EXECUTIVE, OrgRoleRequiredMixin, org_nav
from apps.shared.selectors import ay_label


def base_context(access, **extra):
    context = {
        "access": access,
        "organization": access.organization,
        "term": access.term,
        "ay": ay_label(access.term.label),
        "org_nav": org_nav(access),
        "active_page": "signoff_page",
    }
    context.update(extra)
    return context


class SignOffOverview(OrgRoleRequiredMixin, TemplateView):
    template_name = "signoffs/signoff.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        access = self.access
        term = access.term
        org = access.organization

        plan = TermPlan.objects.filter(term=term).first()
        notes_count = HandoverNote.objects.filter(term=term).count()
        notes_org = HandoverNote.objects.filter(
            term=term, scope=HandoverNote.Scope.ORGANIZATION
        ).count()
        notes_comm = HandoverNote.objects.filter(
            term=term, scope=HandoverNote.Scope.COMMITTEE
        ).count()

        exec_memberships = list(
            Membership.objects.filter(organization=org, term=term, role=EXECUTIVE)
            .select_related("user")
            .order_by("created_at")
        )
        active_exec_users = [m.user for m in exec_memberships]

        sign_offs = {
            s.executive_id: s
            for s in TermSignOff.objects.filter(term=term).select_related("executive")
        }

        exec_status_list = []
        for u in active_exec_users:
            vote = sign_offs.get(u.pk)
            exec_status_list.append(
                {
                    "user": u,
                    "has_voted": vote is not None,
                    "decision": vote.decision if vote else "PENDING",
                    "feedback": vote.feedback if vote else "",
                    "submitted_at": vote.submitted_at if vote else None,
                    "is_me": u.pk == self.request.user.pk,
                }
            )

        my_vote = sign_offs.get(self.request.user.pk)
        can_initiate = (
            access.is_executive
            and term.status == Term.Status.ACTIVE
            and plan is not None
        )
        can_vote = access.is_executive and term.status == Term.Status.PENDING_SIGNOFF

        approved_count = sum(1 for e in exec_status_list if e["decision"] == "APPROVED")
        total_execs = len(exec_status_list)

        context.update(
            base_context(
                access,
                plan=plan,
                notes_count=notes_count,
                notes_org=notes_org,
                notes_comm=notes_comm,
                exec_status_list=exec_status_list,
                my_vote=my_vote,
                can_initiate=can_initiate,
                can_vote=can_vote,
                approved_count=approved_count,
                total_execs=total_execs,
            )
        )
        return context


class SignOffInitiate(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)
    require_open_term = True

    def post(self, request, org_id):
        access = self.access
        term = access.term
        org = access.organization

        plan = TermPlan.objects.filter(term=term).first()
        if not plan:
            messages.error(
                request,
                "You must set up the next A.Y. in 'Next A.Y.' before initiating sign-off.",
            )
            return redirect(reverse("signoff_page", args=[org.pk]))

        with transaction.atomic():
            term.status = Term.Status.PENDING_SIGNOFF
            term.save(update_fields=["status"])
            TermSignOff.objects.filter(term=term).delete()

        others = [
            m.user
            for m in Membership.objects.filter(
                organization=org, term=term, role=EXECUTIVE
            ).exclude(user=request.user)
        ]
        who = request.user.get_full_name() or request.user.username
        notify(
            others,
            f"{who} opened the executive sign-off for {org.name}. Please review transition notes and vote.",
            reverse("signoff_page", args=[org.pk]),
        )
        messages.success(
            request,
            "Executive sign-off is open. Review all handover documents and cast your decision.",
        )
        return redirect(reverse("signoff_page", args=[org.pk]))


class SignOffVote(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)

    def post(self, request, org_id):
        access = self.access
        term = access.term
        org = access.organization

        if term.status != Term.Status.PENDING_SIGNOFF:
            messages.error(request, "This A.Y. is not currently awaiting sign-off votes.")
            return redirect(reverse("signoff_page", args=[org.pk]))

        decision = request.POST.get("decision", "").strip()
        feedback = request.POST.get("feedback", "").strip()

        if decision not in (TermSignOff.Decision.APPROVED, TermSignOff.Decision.CHANGES_REQUESTED):
            messages.error(request, "Choose whether to approve or request changes.")
            return redirect(reverse("signoff_page", args=[org.pk]))

        if decision == TermSignOff.Decision.CHANGES_REQUESTED:
            if not feedback:
                messages.error(request, "Provide specific feedback when requesting changes.")
                return redirect(reverse("signoff_page", args=[org.pk]))

            with transaction.atomic():
                TermSignOff.objects.update_or_create(
                    term=term,
                    executive=request.user,
                    defaults={"decision": decision, "feedback": feedback},
                )
                # Revert term to ACTIVE so outgoing team can revise notes
                term.status = Term.Status.ACTIVE
                term.save(update_fields=["status"])
                # Clear all approvals
                TermSignOff.objects.filter(term=term).delete()

            others = [
                m.user
                for m in Membership.objects.filter(
                    organization=org, term=term, role=EXECUTIVE
                ).exclude(user=request.user)
            ]
            who = request.user.get_full_name() or request.user.username
            notify(
                others,
                f"{who} requested changes on {org.name}'s transition: {feedback}",
                reverse("signoff_page", args=[org.pk]),
            )
            messages.info(
                request,
                f"Changes requested: '{feedback}'. The term has returned to Active status for revisions.",
            )
            return redirect(reverse("signoff_page", args=[org.pk]))

        # Decision is APPROVED
        with transaction.atomic():
            Term.objects.select_for_update().get(pk=term.pk)
            TermSignOff.objects.update_or_create(
                term=term,
                executive=request.user,
                defaults={"decision": decision, "feedback": feedback},
            )

            active_exec_ids = set(
                Membership.objects.filter(organization=org, term=term, role=EXECUTIVE).values_list(
                    "user_id", flat=True
                )
            )
            approved_ids = set(
                TermSignOff.objects.filter(
                    term=term, decision=TermSignOff.Decision.APPROVED
                ).values_list("executive_id", flat=True)
            )

            if active_exec_ids.issubset(approved_ids):
                # Unanimous consensus reached!
                # 1. Close current term
                term.status = Term.Status.CLOSED
                term.save(update_fields=["status"])

                # 2. Activate next term from TermPlan
                plan = TermPlan.objects.get(term=term)
                new_term = Term.objects.create(
                    organization=org,
                    label=plan.label,
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    status=Term.Status.ACTIVE,
                )

                # 3. Create initial leadership for the new term
                for exec_id in active_exec_ids:
                    Membership.objects.create(
                        user_id=exec_id,
                        organization=org,
                        term=new_term,
                        role=Membership.Role.EXECUTIVE,
                        valid_from=new_term.start_date,
                        valid_until=new_term.end_date,
                        appointment_note=f"Rolled over from {term.label} handover approval",
                    )

                # 4. Remove the plan since it has now become the active term
                plan.delete()

                # 5. Broadcast to all members
                all_members = list({
                    m.user_id: m.user
                    for m in Membership.objects.filter(
                        organization=org, term=term
                    ).select_related("user")
                }.values())
                notify(
                    all_members,
                    f"Transition complete for {org.name}! {new_term.label} is now active.",
                    reverse("organization_detail", args=[org.pk]),
                )
                messages.success(
                    request,
                    f"Consensus achieved! {term.label} is officially closed and {new_term.label} is now live.",
                )
                return redirect(reverse("organization_detail", args=[org.pk]))

        messages.success(
            request,
            "Your approval was recorded. Waiting for all active Executives to approve.",
        )
        return redirect(reverse("signoff_page", args=[org.pk]))


class SignOffCancel(OrgRoleRequiredMixin, View):
    allowed_roles = (EXECUTIVE,)

    def post(self, request, org_id):
        access = self.access
        term = access.term
        org = access.organization

        if term.status == Term.Status.PENDING_SIGNOFF:
            with transaction.atomic():
                term.status = Term.Status.ACTIVE
                term.save(update_fields=["status"])
                TermSignOff.objects.filter(term=term).delete()
            messages.info(request, "Sign-off was cancelled. The term is back to Active status.")

        return redirect(reverse("signoff_page", args=[org.pk]))
