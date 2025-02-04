from logging import getLogger
from discord.ext.commands import GroupCog, Bot
from discord import Interaction, app_commands as ac, Member, TextStyle, Emoji, SelectOption, ui, ButtonStyle
from discord.ui import Modal, TextInput
from models import Player, Unit, ActiveUnit, UnitStatus, Upgrade, Medals
from customclient import CustomClient

logger = getLogger(__name__)

class Admin(GroupCog):
    """
    Admin commands for the bot
    """
    def __init__(self, bot: Bot):
        """
        Initialize the Admin cog
        """
        super().__init__()
        self.bot = bot
        self.session = bot.session
        # self.interaction_check = self.is_mod # disabled for development, as those roles don't exist on the dev guild

    async def is_mod(self, interaction: Interaction):
        """
        Check if the user is a moderator
        """
        valid = any(interaction.user.has_role(role) for role in self.bot.mod_roles)
        if not valid:
            logger.warning(f"{interaction.user.name} tried to use admin commands")
        return valid
    
    @ac.command(name="recpoint", description="Give or remove a number of requisition points from a player")
    @ac.describe(player="The player to give or remove points from")
    @ac.describe(points="The number of points to give or remove")
    async def recpoint(self, interaction: Interaction, player: Member, points: int):
        """
        Give or remove a number of requisition points from a player

        Args:
            player (Member): The player to give or remove points from
            points (int): The number of points to give or remove
        """
        # find the player by discord id
        player = self.session.query(Player).filter(Player.discord_id == player.id).first()
        if not player:
            await interaction.response.send_message("User doesn't have a Meta Campaign company", ephemeral=self.bot.use_ephemeral)
            return
        
        # update the player's rec points
        player.rec_points += points
        self.session.commit()
        logger.debug(f"User {player.name} now has {player.rec_points} requisition points")
        await interaction.response.send_message(f"{player.name} now has {player.rec_points} requisition points", ephemeral=self.bot.use_ephemeral)

    @ac.command(name="bulk_recpoint", description="Give or remove a number of requisition points from a set of players")
    @ac.describe(points="The number of points to give or remove")
    @ac.describe(status="Status of the unit (Inactive = 0, Active = 1, MIA = 2, KIA = 3)")
    async def bulk_recpoint(self, interaction: Interaction, status: str, points: int):
        """
        Give or remove a number of requisition points from a set of players

        Args:
            status (str): The status of the units to update
            points (int): The number of points to give or remove
        """
        # Find all units with corresponding Enum status
        status_enum = UnitStatus(status)
        units = self.session.query(Unit).filter(Unit.status == status_enum).all()
        for unit in units:
            # Find player of each unit and update their recpoints
            player = unit.player
            player.rec_points += points
            logger.debug(f"User {player.name} now has {player.rec_points} requisition points")
        self.session.commit()
        await interaction.response.send_message(f"Players of units of the status {status} have received {points} requisition points", ephemeral=self.bot.use_ephemeral)
    
    @ac.command(name="bulk_recpoint_by_name", description="Give or remove a number of requisition points from a set of players by name")
    @ac.describe(points="The number of requisition points to give or remove")
    async def bulk_recpoint_by_name(self, interaction: Interaction, points: int):
        """
        Give or remove a number of requisition points from a set of players by name

        Args:
            points (int): The number of requisition points to give or remove
        """
        brp_modal = Modal(title="Bulk Requisition Points by Name", custom_id="bulk_recpoint_by_name")
        brp_modal.add_item(TextInput(label="Player names", custom_id="player_names", style=TextStyle.paragraph))
        async def brp_modal_callback(interaction: Interaction):
            player_names = interaction.data["components"][0]["components"][0]["value"]
            logger.debug(f"Received player names: {player_names}")
            if "\n" in player_names[:40]:
                player_names = set(player_names.split("\n"))
            else:
                player_names = set(player_names.split(","))
            player_names = [name.strip() for name in player_names]
            if len(player_names) == 0:
                await interaction.response.send_message("No player names provided", ephemeral=self.bot.use_ephemeral)
                return
            logger.debug(f"Parsed player names: {player_names}")
            # we need to convert the discord names to discord ids, then convert those to Player objects
            members: list[Member] = await interaction.guild.fetch_members(limit=None).flatten()
            chosen_members = {member for member in members if member.global_name in player_names}
            discord_ids = {member.id for member in chosen_members}
            players = self.session.query(Player).filter(Player.discord_id.in_(discord_ids)).all()
            failed_players = []
            for player in players:
                if player.rec_points + points < 0:
                    failed_players.append(player.name)
                    continue
                player.rec_points += points
            self.session.commit()
            await interaction.response.send_message(f"Players {chosen_members} have been updated, {', '.join(failed_players)} failed", ephemeral=self.bot.use_ephemeral)

        brp_modal.on_submit = brp_modal_callback
        await interaction.response.send_modal(brp_modal)


    @ac.command(name="bonuspay", description="Give or remove a number of bonus pay from a player")
    @ac.describe(player="The player to give or remove bonus pay from")
    @ac.describe(points="The number of bonus pay to give or remove")
    async def bonuspay(self, interaction: Interaction, player: Member, points: int):
        """
        Give or remove a number of bonus pay from a player

        Args:
            player (Member): The player to give or remove bonus pay from
            points (int): The number of bonus pay to give or remove
        """
        # find the player by discord id
        player = self.session.query(Player).filter(Player.discord_id == player.id).first()
        if not player:
            await interaction.response.send_message("User doesn't have a Meta Campaign company", ephemeral=self.bot.use_ephemeral)
            return
        
        # update the player's bonus pay
        player.bonus_pay += points
        self.session.commit()
        logger.debug(f"User {player.name} now has {player.bonus_pay} bonus pay")
        await interaction.response.send_message(f"{player.name} now has {player.bonus_pay} bonus pay", ephemeral=self.bot.use_ephemeral)

    @ac.command(name="bulk_bonuspay", description="Give or remove a number of bonus pay from a set of players")
    @ac.describe(points="The number of bonus pay to give or remove")
    @ac.describe(status="Status of the unit (Inactive = 0, Active = 1, MIA = 2, KIA = 3)")
    async def bulk_bonus_pay(self, interaction: Interaction, status: str, points: int):
        """
        Give or remove a number of bonus pay from a set of players

        Args:
            status (str): The status of the units to update
            points (int): The number of bonus pay to give or remove
        """
        # Find all units with corresponding Enum status
        status_enum = UnitStatus(status)
        units = self.session.query(Unit).filter(Unit.status == status_enum).all()
        for unit in units:
            # Find player of each unit and update their bonuspay
            player = unit.player
            player.bonus_pay += points
            logger.debug(f"User {player.name} now has {player.bonus_pay} requisition points")
        self.session.commit()
        await interaction.response.send_message(f"Players of units of the status {status} have received {points} bonus pay", ephemeral=self.bot.use_ephemeral)

    @ac.command(name="bulk_bonuspay_by_name", description="Give or remove a number of bonus pay from a set of players by name")
    @ac.describe(points="The number of bonus pay to give or remove")
    async def bulk_bonuspay_by_name(self, interaction: Interaction, points: int):
        """
        Give or remove a number of bonus pay from a set of players by name

        Args:
            points (int): The number of bonus pay to give or remove
        """
        bbp_modal = Modal(title="Bulk Bonus Pay by Name", custom_id="bulk_bonuspay_by_name")
        bbp_modal.add_item(TextInput(label="Player names", custom_id="player_names", style=TextStyle.paragraph))
        async def bbp_modal_callback(interaction: Interaction):
            player_names = interaction.data["components"][0]["components"][0]["value"]
            logger.debug(f"Received player names: {player_names}")
            if "\n" in player_names[:40]:
                player_names = set(player_names.split("\n"))
            else:
                player_names = set(player_names.split(","))
            player_names = [name.strip() for name in player_names]
            if len(player_names) == 0:
                await interaction.response.send_message("No player names provided", ephemeral=self.bot.use_ephemeral)
                return
            logger.debug(f"Parsed player names: {player_names}")
            # we need to convert the discord names to discord ids, then convert those to Player objects
            members: list[Member] = await interaction.guild.fetch_members(limit=None).flatten()
            chosen_members = {member for member in members if member.global_name in player_names}
            discord_ids = {member.id for member in chosen_members}
            players = self.session.query(Player).filter(Player.discord_id.in_(discord_ids)).all()
            failed_players = []
            for player in players:
                if player.bonus_pay + points < 0:
                    failed_players.append(player.name)
                    continue
                player.bonus_pay += points
            self.session.commit()
            await interaction.response.send_message(f"Players {chosen_members} have been updated, {', '.join(failed_players)} failed", ephemeral=self.bot.use_ephemeral)

        bbp_modal.on_submit = bbp_modal_callback
        await interaction.response.send_modal(bbp_modal)

    @ac.command(name="activateunits", description="Activate multiple units")
    async def activateunits(self, interaction: Interaction):
        """
        Activate multiple units
        """ 
        modal = Modal(title="Activate Units", custom_id="activate_units")
        modal.add_item(TextInput(label="Unit names", custom_id="unit_names", style=TextStyle.long))
        async def modal_callback(interaction: Interaction):
            unit_names = interaction.data["components"][0]["components"][0]["value"]
            logger.debug(f"Received unit names: {unit_names}")
            if "\n" in unit_names[:40]:
                unit_names = unit_names.split("\n")
            else:
                unit_names = unit_names.split(",")
            logger.debug(f"Parsed unit names: {unit_names}")
            activated = []
            not_found = []
            for unit_name in unit_names:
                unit = self.session.query(Unit).filter(Unit.name == unit_name).first()
                if unit:
                    activated.append(unit.name)
                    active_unit = ActiveUnit(unit_id=unit.id, player_id=unit.player_id)
                    self.session.add(active_unit)
                    logger.debug(f"Activated unit: {unit.name}")
                else:
                    not_found.append(unit_name)
                    logger.debug(f"Unit not found: {unit_name}")
                try:
                    self.session.commit()
                except Exception as e:
                    logger.error(f"Error committing to database: {e}")
                    await interaction.response.send_message(f"Error committing to database: {e}", ephemeral=self.bot.use_ephemeral)
            await interaction.response.send_message(f"Activated {activated}, not found {not_found}", ephemeral=self.bot.use_ephemeral)
            logger.debug(f"Activation results - Activated: {activated}, Not found: {not_found}")
        modal.on_submit = modal_callback
                
        await interaction.response.send_modal(modal)

    @ac.command(name="create_medal", description="Create a medal")
    @ac.describe(name="The name of the medal")
    @ac.describe(left_emote="The emote id to use for the left side of the medal")
    @ac.describe(center_emote="The emote id to use for the center of the medal")
    @ac.describe(right_emote="The emote id to use for the right side of the medal")
    async def create_medal(self, interaction: Interaction, name: str, left_emote: str, center_emote: str, right_emote: str):
        """
        Create a medal

        Args:
            name (str): The name of the medal
            left_emote (str): The emote id to use for the left side of the medal
            center_emote (str): The emote id to use for the center of the medal
            right_emote (str): The emote id to use for the right side of the medal
        """
        # check if the emotes are valid
        _left_emote: Emoji = await self.bot.fetch_application_emoji(int(left_emote))
        _center_emote: Emoji = await self.bot.fetch_application_emoji(int(center_emote))
        _right_emote: Emoji = await self.bot.fetch_application_emoji(int(right_emote))
        if not all([isinstance(emote, Emoji) for emote in [_left_emote, _center_emote, _right_emote]]):
            await interaction.response.send_message("Invalid emote", ephemeral=self.bot.use_ephemeral)
            return
        # create the medal

        self.bot.medal_emotes[name] = [str(_left_emote), str(_center_emote), str(_right_emote)]
        logger.debug(f"Medal {name} created with emotes {left_emote}, {center_emote}, {right_emote}")
        await interaction.response.send_message(f"Medal {name} created", ephemeral=self.bot.use_ephemeral)

    @ac.command(name="award_medal", description="Award a medal to a player")
    @ac.describe(player="The player to award the medal to")
    @ac.describe(medal="The name of the medal")
    async def award_medal(self, interaction: Interaction, player: Member, medal: str):
        """
        Award a medal to a player

        Args:
            player (Member): The player to award the medal to
            medal (str): The name of the medal
        """
        # find the player by discord id
        _player: Player = self.session.query(Player).filter(Player.discord_id == player.id).first()
        if not _player:
            await interaction.response.send_message("User doesn't have a Meta Campaign company", ephemeral=self.bot.use_ephemeral)
            return
        # if the player already has a medal with that name, send a message saying so
        _medal = self.session.query(Medals).filter(Medals.name == medal).filter(Medals.player_id == _player.id).first()
        if _medal:
            await interaction.response.send_message(f"{player.name} already has the medal {medal}", ephemeral=self.bot.use_ephemeral)
            return
        # add the medal to the player
        _medal = Medals(name=medal, player_id=_player.id)
        self.session.add(_medal)
        self.session.commit()
        await interaction.response.send_message(f"{player.name} has been awarded the medal {medal}", ephemeral=self.bot.use_ephemeral)

    @ac.command(name="create_unit_type", description="Create a new unit type")
    @ac.describe(name="The name of the unit type")
    async def create_unit_type(self, interaction: Interaction, name: str):
        """
        Create a new unit type

        Args:
            name (str): The name of the unit type
        """
        if len(name) > 15:
            await interaction.response.send_message("Unit type name is too long, please use a shorter name", ephemeral=self.bot.use_ephemeral)
            return
        if not self.bot.config.get("unit_types"):
            self.bot.config["unit_types"] = {name}
        else:
            self.bot.config["unit_types"].add(name) # unit_types is a set, so we can just append
        await self.bot.resync_config()
        await interaction.response.send_message(f"Unit type {name} created", ephemeral=self.bot.use_ephemeral)

    @ac.command(name="refresh_stats", description="Refresh the statistics and dossiers for all players")
    async def refresh_stats(self, interaction: Interaction):
        """
        Refresh the statistics and dossiers for all players
        """
        await interaction.response.send_message("Refreshing statistics and dossiers for all players", ephemeral=self.bot.use_ephemeral)
        self.session.expire_all()
        for player in self.session.query(Player).all():
            self.bot.queue.put_nowait((1, player)) # make the bot think the player was edited, using nowait to avoid yielding control
        await interaction.followup.send("Refreshed statistics and dossiers for all players", ephemeral=self.bot.use_ephemeral)

    @ac.command(name="specialupgrade", description="Give a player a one-off or relic item")
    @ac.describe(player="The player to give the item to")
    @ac.describe(name="The name of the item")
    async def specialupgrade(self, interaction: Interaction, player: Member, name: str):
        """
        Give a player a one-off or relic item

        Args:
            player (Member): The player to give the item to
            name (str): The name of the item
        """
        _player = self.session.query(Player).filter(Player.discord_id == player.id).first()
        if not _player:
            await interaction.response.send_message("Player does not have a Meta Campaign company", ephemeral=self.bot.use_ephemeral)
            return
        _active_unit = self.session.query(ActiveUnit).filter(ActiveUnit.player_id == _player.id).first()
        if not _active_unit:
            await interaction.response.send_message("Player does not have an active unit", ephemeral=self.bot.use_ephemeral)
            return
        _unit = self.session.query(Unit).filter(Unit.id == _active_unit.unit_id).first()
        if not _unit:
            await interaction.response.send_message("Player's unit does not exist, please contact the Quartermaster", ephemeral=self.bot.use_ephemeral)
            return
        # create an Upgrade with the given name, type "SPECIAL", and the unit as the parent
        if len(name) > 30:
            await interaction.response.send_message("Name is too long, please use a shorter name", ephemeral=self.bot.use_ephemeral)
            return
        upgrade = Upgrade(name=name, type="SPECIAL", unit_id=_unit.id)
        self.session.add(upgrade)
        self.session.commit()
        await interaction.response.send_message(f"Special upgrade {name} given to {_player.name}", ephemeral=self.bot.use_ephemeral)

    @ac.command(name="remove_unit", description="Remove a unit from a player")
    @ac.describe(player="The player to remove the unit from")
    async def remove_unit(self, interaction: Interaction, player: Member):
        """
        Remove a unit from a player

        Args:
            player (Member): The player to remove the unit from
        """
        # we need to make a modal for this, as we need a dropdown for the unit type
        class UnitSelect(ui.Select):
            def __init__(self, player_units):
                options = [SelectOption(label=unit.name, value=unit.id) for unit in player_units]
                super().__init__(placeholder="Select name of unit you want to removed", options=options)

            async def callback(self, interaction: Interaction):
                await interaction.response.defer(ephemeral=True)

        class CreateUnitView(ui.View):
            def __init__(self, player_units):
                super().__init__()
                self.session = CustomClient().session  # can't use self.session because this is a nested class, so we use the singleton reference
                self.add_item(UnitSelect(player_units))

            @ui.button(label="Remove Unit", style=ButtonStyle.primary)
            async def create_unit_callback(self, interaction: Interaction, button: ui.Button):

                # create the unit in the database
                unit_id = self.children[1].values[0]
                unit = self.session.query(Unit).filter(Unit.player_id == player.id).filter(Unit.id == unit_id).first()
                logger.debug(f"Unit with the id {unit_id} has been selected to remove")
                if not unit:
                    await interaction.response.send_message("Unit not found", ephemeral=CustomClient().use_ephemeral)
                    return
                self.bot.queue.put_nowait((2, unit))
                self.session.delete(unit)
                self.session.commit()
                logger.debug(f"Unit with the id {unit_id} was deleted from player {player.name}")
                await interaction.response.send_message(f"Unit {unit.name} has been removed", ephemeral=CustomClient().use_ephemeral)
                

        # Checks if the Player has a Meta Company and If that company has a name
        player = self.session.query(Player).filter(Player.discord_id == interaction.user.id).first()
        if not player:
            await interaction.response.send_message(f"{player.name} doesn't have a Meta Campaign company", ephemeral=CustomClient().use_ephemeral)
            return
        if len(player.units) == 0:
            await interaction.response.send_message(f"{player.name} doesn't have a unit to remove", ephemeral=CustomClient().use_ephemeral)
            return
        player_units = self.session.query(Unit).filter(Unit.player_id == player.id).all()
        view = CreateUnitView(player_units)
        await interaction.response.send_message("Please select the unit type and enter the unit name", view=view, ephemeral=CustomClient().use_ephemeral)

    @ac.command(name="remove_unittype", description="Remove a unit type from the game")
    @ac.describe(name="The name of the unit type to remove")
    async def remove_unittype(self, interaction: Interaction, name: str):
        if name in self.bot.config.get("unit_types"):
            self.bot.config["unit_types"].remove(name)
            await self.bot.resync_config()
        units = self.session.query(Unit).filter(Unit.type == name).filter(Unit.active_unit == None).all()
        for unit in units:
            unit.legacy = True
            if unit.status == UnitStatus.INACTIVE:
                unit.status = UnitStatus.LEGACY
            logger.debug(f"Unit {unit.name} has been set to legacy")
        self.session.commit()

        await interaction.response.send_message(f"Unit type {name} removed", ephemeral=self.bot.use_ephemeral)


bot: Bot = None
async def setup(_bot: Bot):
    """
    Setup the Admin cog

    Args:
        _bot (Bot): The bot instance
    """
    global bot
    bot = _bot
    logger.info("Setting up Admin cog")
    await bot.add_cog(Admin(bot))
    await bot.tree.sync()

async def teardown():
    """
    Teardown the Admin cog
    """
    logger.info("Tearing down Admin cog")
    bot.remove_cog(Admin.__name__) # remove_cog takes a string, not a class
