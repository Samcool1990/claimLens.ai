def policy_dict(policy):
    return {"id": policy.id, "carrier": policy.carrier, "policy_number": policy.policy_number,
            "product_name": policy.product_name, "jurisdiction": policy.jurisdiction,
            "policy_holder": policy.policy_holder}


def version_dict(version):
    return {"id": version.id, "effective_date": version.effective_date,
            "expiry_date": version.expiry_date, "version_label": version.version_label}


def document_dict(document):
    return {"id": document.id, "policy_version_id": document.policy_version_id,
            "filename": document.filename, "media_type": document.media_type,
            "byte_size": document.byte_size, "sha256": document.sha256,
            "validation_state": document.validation_state}
