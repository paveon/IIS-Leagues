from django.db.models import Q


def force_join_team(team, player):
    join_clan(team.clan, player)
    join_team(team, player, None)


def leave_team(team, player):
    team.team_members.remove(player)

    if team.leader == player:
        # Leader is leaving
        team.leader = team.team_members.first()

        # If there were no members left, check if there are pending players
        if not team.leader:
            # If team has clan, pick first pending player from this clan
            if team.clan:
                new_member = team.team_pendings.filter(clan=team.clan).first()
            else:
                new_member = team.team_pendings.first()

            if new_member:
                team.team_pendings.remove(new_member)
                team.team_members.add(new_member)
                team.leader = new_member
        team.save()


def join_team(team, player, response):
    # Player must be member of parent clan
    if team.clan and not player.clan:
        if team.clan in player.clan_pendings.all():
            # Player is already waiting to be accepted into the clan
            player.team_pendings.add(team)
        else:
            response['need_clan'] = (team.clan.name, team.clan.id)
    else:
        if team.leader:
            player.team_pendings.add(team)
        else:
            # Team has no members, join immediately and become new leader
            team.team_members.add(player)
            team.leader = player
            if team.clan_pending and player.clan != team.clan_pending:
                team.clan_pending = None

            team.save()


def force_leave_clan(clan, player):
    # Leave all clan teams when force leaving clan
    for team in player.teams.filter(clan=clan):
        leave_team(team, player)
    leave_clan(clan, player, None)


def leave_clan(clan, player, response):
    clan_teams = player.teams.filter(clan=clan)
    if clan_teams.exists():
        # Player is in clan team
        teams = [(team.name, team.id) for team in clan_teams]
        response['has_clan_teams'] = teams
    else:
        clan.clan_members.remove(player)
        if clan.leader == player:
            # Leader is leaving
            clan.leader = clan.clan_members.first()
            if not clan.leader:
                # Clan had no members left, pick first pending player
                new_member = clan.clan_pendings.first()
                if new_member:
                    clan.clan_pendings.remove(new_member)
                    clan.clan_members.add(new_member)
                    clan.leader = new_member
            clan.save()


def join_clan(clan, player):
    if clan.leader:
        player.clan_pendings.add(clan)
    else:
        # Clan has no members, join immediately and become new leader
        # First remove all other clan pendings
        pendings = player.clan_pendings.all()
        player.clan_pendings.remove(*pendings)

        # Also remove pendings of teams from other clans, ignore teams without clan
        pendings = player.team_pendings.filter(Q(clan__isnull=False) & ~Q(clan=clan))
        player.team_pendings.remove(*pendings)

        player.clan = clan
        player.save()
        clan.leader = player
        clan.save()
