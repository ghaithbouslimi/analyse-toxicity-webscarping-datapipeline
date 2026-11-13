def decouper(token_ids, tokenizer, max_length):
    capacity = max_length - tokenizer.num_special_tokens_to_add(pair=False)
    if capacity <= 0:
        raise ValueError("Capacité tokenizer invalide")
    for start in range(0, len(token_ids), capacity):
        yield tokenizer.prepare_for_model(
            token_ids[start : start + capacity],
            add_special_tokens=True,
            return_attention_mask=True,
            truncation=False,
        )
