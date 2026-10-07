# Condições de evolução específicas do Pokémon GO.
# Chave: (species_id_origem, species_id_destino)  ← números nacionais da Pokédex.
# Valor: instrução curta em PT-BR exibida na seção 🧬 da wishlist.
# Pokémon sem entrada: evoluem só com doces, sem requisito extra.

GO_CONDITIONS: dict[tuple[int, int], str] = {

    # ── Eevee (133) ──────────────────────────────────────────────────────────
    (133, 134): "Aleatório (Vaporeão / Jolteon / Flareon)",
    (133, 135): "Aleatório (Vaporeão / Jolteon / Flareon)",
    (133, 136): "Aleatório (Vaporeão / Jolteon / Flareon)",
    (133, 196): "Evoluir de dia + 10 km como parceiro",
    (133, 197): "Evoluir à noite + 10 km como parceiro",
    (133, 470): "Usar Isca Musgosa ou Pedra da Folha",
    (133, 471): "Usar Isca Glacial ou Pedra do Gelo",
    (133, 700): "70 corações como parceiro",

    # ── Iscas (Lure Modules) ─────────────────────────────────────────────────
    (82,  462): "Usar Isca Magnética ou Pedra do Trovão",   # Magneton → Magnezone
    (299, 476): "Usar Isca Magnética ou Pedra do Trovão",   # Nosepass → Probopass

    # ── Parceiro de Aventura (Buddy km / corações) ────────────────────────────
    (349, 350): "20 km como parceiro",     # Feebas → Milotic
    (440, 113): "15 km como parceiro",     # Happiny → Chansey
    (439, 122): "15 km como parceiro",     # Mime Jr. → Mr. Mime (Kanto)
    (438, 185): "15 km como parceiro",     # Bonsly → Sudowoodo
    (527, 528): "1 km como parceiro",      # Woobat → Swoobat
    (231, 232): "Parceiro de aventura",    # Phanpy → Donphan (andar com ele)

    # ── Sinnoh Stone ─────────────────────────────────────────────────────────
    (108, 463): "Pedra de Sinnoh",   # Lickitung → Lickilicky
    (112, 464): "Pedra de Sinnoh",   # Rhydon → Rhyperior
    (114, 465): "Pedra de Sinnoh",   # Tangela → Tangrowth
    (125, 466): "Pedra de Sinnoh",   # Electabuzz → Electivire
    (126, 467): "Pedra de Sinnoh",   # Magmar → Magmortar
    (176, 468): "Pedra de Sinnoh",   # Togetic → Togekiss
    (190, 424): "Pedra de Sinnoh",   # Aipom → Ambipom
    (193, 469): "Pedra de Sinnoh",   # Yanma → Yanmega
    (198, 430): "Pedra de Sinnoh",   # Murkrow → Honchkrow
    (200, 429): "Pedra de Sinnoh",   # Misdreavus → Mismagius
    (207, 472): "Pedra de Sinnoh",   # Gligar → Gliscor
    (215, 461): "Pedra de Sinnoh",   # Sneasel (Kanto) → Weavile
    (221, 473): "Pedra de Sinnoh",   # Piloswine → Mamoswine
    (233, 474): "Pedra de Sinnoh",   # Porygon2 → Porygon-Z
    (281, 475): "Pedra de Sinnoh",   # Kirlia → Gallade
    (315, 407): "Pedra de Sinnoh",   # Roselia → Roserade
    (356, 477): "Pedra de Sinnoh",   # Dusclops → Dusknoir
    (361, 478): "Pedra de Sinnoh",   # Snorunt → Froslass

    # ── Unova Stone ──────────────────────────────────────────────────────────
    (511, 512): "Pedra de Unova",    # Pansage → Simisage
    (513, 514): "Pedra de Unova",    # Pansear → Simisear
    (515, 516): "Pedra de Unova",    # Panpour → Simipour
    (517, 518): "Pedra de Unova",    # Munna → Musharna
    (572, 573): "Pedra de Unova",    # Minccino → Cinccino
    (603, 604): "Pedra de Unova",    # Eelektrik → Eelektross
    (608, 609): "Pedra de Unova",    # Lampent → Chandelure

    # ── Troca (grátis se recebido via troca) ─────────────────────────────────
    (61,  186): "Grátis se recebido via troca",   # Poliwhirl → Politoed
    (64,   65): "Grátis se recebido via troca",   # Kadabra → Alakazam
    (67,   68): "Grátis se recebido via troca",   # Machoke → Machamp
    (75,   76): "Grátis se recebido via troca",   # Graveler (Kanto) → Golem
    (93,   94): "Grátis se recebido via troca",   # Haunter → Gengar
    (95,  208): "Grátis se recebido via troca",   # Onix → Steelix
    (117, 230): "Grátis se recebido via troca",   # Seadra → Kingdra
    (123, 212): "Grátis se recebido via troca",   # Scyther → Scizor
    (137, 233): "Grátis se recebido via troca",   # Porygon → Porygon2
    (525, 526): "Grátis se recebido via troca",   # Boldore → Gigalith
    (533, 534): "Grátis se recebido via troca",   # Gurdurr → Conkeldurr
    (588, 589): "Grátis se recebido via troca",   # Karrablast → Escavalier
    (616, 617): "Grátis se recebido via troca",   # Shelmet → Accelgor

    # ── Condições especiais de geração Hisui / Galar ─────────────────────────
    (57,  1009): "Derrotar 30 Psíquico/Fantasma como parceiro",  # Primeape → Annihilape
    (83,   865): "10 arremessos Excelentes como parceiro",        # Galarian Farfetch'd → Sirfetch'd
    (211,  904): "Vencer 10 Raids como parceiro",                 # Hisuian Qwilfish → Overqwil
    (215,  903): "7 km como parceiro + evoluir de dia",           # Hisuian Sneasel → Sneasler
    (217,  901): "Evoluir durante Lua Cheia",                     # Ursaring → Ursaluna
    (234,  899): "20 furtividades como parceiro",                 # Stantler → Wyrdeer
    (550,  902): "10 arremessos Excelentes como parceiro",        # Basculin → Basculegion
}
