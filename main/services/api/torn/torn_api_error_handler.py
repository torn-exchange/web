class TornApiErrorHandler:
    @classmethod
    def handle_error(cls, code):
        switch = {
            0: cls.handle_unknown_error,
            1: cls.handle_key_empty,
            2: cls.handle_incorrect_key,
            3: cls.handle_wrong_type,
            4: cls.handle_wrong_fields,
            5: cls.handle_too_many_requests,
            6: cls.handle_incorrect_id,
            7: cls.handle_id_entity_relation,
            8: cls.handle_ip_block,
            9: cls.handle_api_disabled,
            10: cls.handle_federal_jail,
            11: cls.handle_key_change_error,
            12: cls.handle_key_read_error,
            13: cls.handle_inactivity,
            14: cls.handle_daily_limit,
            15: cls.handle_temporary_error,
            16: cls.handle_access_level,
            17: cls.handle_backend_error,
            18: cls.handle_api_paused,
            19: cls.handle_migration,
            20: cls.handle_race_not_finished,
            21: cls.handle_incorrect_category,
        }

        return switch.get(code, lambda: "Unknown error code.")()

    @classmethod
    def handle_unknown_error(cls):
        return "Unknown error: Unhandled error, should not occur."

    @classmethod
    def handle_key_empty(cls):
        return "Key is empty: Private key is empty in current request."

    @classmethod
    def handle_incorrect_key(cls):
        return "Incorrect Key: Private key is wrong/incorrect format."

    @classmethod
    def handle_wrong_type(cls):
        return "Wrong type: Requesting an incorrect basic type."

    @classmethod
    def handle_wrong_fields(cls):
        return "Wrong fields: Requesting incorrect selection fields."

    @classmethod
    def handle_too_many_requests(cls):
        return "Too many requests: Requests are blocked for a small period of time because of too many requests per user (max 100 per minute)."

    @classmethod
    def handle_incorrect_id(cls):
        return "Incorrect ID: Wrong ID value."

    @classmethod
    def handle_id_entity_relation(cls):
        return "Incorrect ID-entity relation: A requested selection is private (e.g., personal data of another user/faction)."

    @classmethod
    def handle_ip_block(cls):
        return "IP block: Current IP is banned for a small period of time because of abuse."

    @classmethod
    def handle_api_disabled(cls):
        return "API disabled: API system is currently disabled."

    @classmethod
    def handle_federal_jail(cls):
        return "Key owner is in federal jail: Current key can't be used because the owner is in federal jail."

    @classmethod
    def handle_key_change_error(cls):
        return "Key change error: You can only change your API key once every 60 seconds."

    @classmethod
    def handle_key_read_error(cls):
        return "Key read error: Error reading key from Database."

    @classmethod
    def handle_inactivity(cls):
        return "Key temporarily disabled due to owner inactivity: The key owner hasn't been online for more than 7 days."

    @classmethod
    def handle_daily_limit(cls):
        return "Daily read limit reached: Too many records have been pulled today by this user from our cloud services."

    @classmethod
    def handle_temporary_error(cls):
        return "Temporary error: An error code specifically for testing purposes that has no dedicated meaning."

    @classmethod
    def handle_access_level(cls):
        return "Access level too low: A selection is being called that this key does not have permission to access."

    @classmethod
    def handle_backend_error(cls):
        return "Backend error occurred, please try again."

    @classmethod
    def handle_api_paused(cls):
        return "API key has been paused by the owner."

    @classmethod
    def handle_migration(cls):
        return "Must be migrated to crimes 2.0."

    @classmethod
    def handle_race_not_finished(cls):
        return "Race not yet finished."

    @classmethod
    def handle_incorrect_category(cls):
        return "Incorrect category: Wrong cat value."
