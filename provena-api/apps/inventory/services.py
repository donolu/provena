from django.db import transaction

from apps.catalogue.models import ProductVariant

from .models import MovementType, StockLevel, StockLot, StockMovement
from .signals import low_stock_alert


def _maybe_alert(level: StockLevel) -> None:
    if level.is_low_stock:
        low_stock_alert.send(
            sender=StockLevel,
            variant=level.variant,
            stock_level=level,
            quantity_available=level.quantity_available,
        )


def get_or_create_stock_level(variant: ProductVariant) -> StockLevel:
    level, _ = StockLevel.objects.get_or_create(variant=variant)
    return level


def _get_locked_stock_level(variant: ProductVariant) -> StockLevel:
    """Ensure the StockLevel row exists and acquire a row-level lock for the current transaction."""
    StockLevel.objects.get_or_create(variant=variant)
    return StockLevel.objects.select_for_update().get(variant=variant)


@transaction.atomic
def receive_stock(
    variant: ProductVariant,
    quantity: int,
    *,
    lot_number: str = "",
    expires_at=None,
    notes: str = "",
    performed_by=None,
) -> tuple[StockLevel, StockLot, StockMovement]:
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    level = _get_locked_stock_level(variant)
    lot = StockLot.objects.create(
        variant=variant,
        lot_number=lot_number,
        quantity_received=quantity,
        quantity_remaining=quantity,
        expires_at=expires_at,
        notes=notes,
    )
    level.quantity_available += quantity
    level.save()
    _maybe_alert(level)
    movement = StockMovement.objects.create(
        variant=variant,
        movement_type=MovementType.INBOUND,
        quantity=quantity,
        quantity_after=level.quantity_available,
        reference=lot_number or str(lot.id),
        notes=notes,
        performed_by=performed_by,
    )
    return level, lot, movement


@transaction.atomic
def adjust_stock(
    variant: ProductVariant,
    delta: int,
    *,
    notes: str,
    performed_by=None,
) -> tuple[StockLevel, StockMovement]:
    if delta == 0:
        raise ValueError("Delta cannot be zero.")
    level = _get_locked_stock_level(variant)
    new_available = level.quantity_available + delta
    if new_available < 0:
        raise ValueError(
            f"Adjustment would result in negative stock ({new_available}). "
            f"Current available: {level.quantity_available}."
        )
    level.quantity_available = new_available
    level.save()
    _maybe_alert(level)
    movement = StockMovement.objects.create(
        variant=variant,
        movement_type=MovementType.ADJUSTMENT,
        quantity=delta,
        quantity_after=level.quantity_available,
        notes=notes,
        performed_by=performed_by,
    )
    return level, movement


@transaction.atomic
def set_low_stock_threshold(variant: ProductVariant, threshold: int) -> StockLevel:
    if threshold < 0:
        raise ValueError("Threshold cannot be negative.")
    level = _get_locked_stock_level(variant)
    level.low_stock_threshold = threshold
    level.save()
    return level


@transaction.atomic
def reserve_stock(
    variant: ProductVariant,
    quantity: int,
    *,
    reference: str = "",
) -> tuple[StockLevel, StockMovement]:
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    level = _get_locked_stock_level(variant)
    if level.quantity_available < quantity:
        raise ValueError(
            f"Insufficient stock. Requested {quantity}, available {level.quantity_available}."
        )
    level.quantity_available -= quantity
    level.quantity_reserved += quantity
    level.save()
    _maybe_alert(level)
    movement = StockMovement.objects.create(
        variant=variant,
        movement_type=MovementType.RESERVED,
        quantity=-quantity,
        quantity_after=level.quantity_available,
        reference=reference,
    )
    return level, movement


@transaction.atomic
def release_reservation(
    variant: ProductVariant,
    quantity: int,
    *,
    reference: str = "",
) -> tuple[StockLevel, StockMovement]:
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    level = _get_locked_stock_level(variant)
    if level.quantity_reserved < quantity:
        raise ValueError(f"Cannot release {quantity} — only {level.quantity_reserved} reserved.")
    level.quantity_reserved -= quantity
    level.quantity_available += quantity
    level.save()
    movement = StockMovement.objects.create(
        variant=variant,
        movement_type=MovementType.UNRESERVED,
        quantity=quantity,
        quantity_after=level.quantity_available,
        reference=reference,
    )
    return level, movement


@transaction.atomic
def dispatch_stock(
    variant: ProductVariant,
    quantity: int,
    *,
    reference: str = "",
    notes: str = "",
) -> tuple[StockLevel, StockMovement]:
    """Remove from reserved when an order ships."""
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    level = _get_locked_stock_level(variant)
    if level.quantity_reserved < quantity:
        raise ValueError(f"Cannot dispatch {quantity} — only {level.quantity_reserved} reserved.")
    level.quantity_reserved -= quantity
    level.save()
    movement = StockMovement.objects.create(
        variant=variant,
        movement_type=MovementType.OUTBOUND,
        quantity=-quantity,
        quantity_after=level.quantity_available,
        reference=reference,
        notes=notes,
    )
    return level, movement


@transaction.atomic
def return_stock(
    variant: ProductVariant,
    quantity: int,
    *,
    notes: str = "",
    performed_by=None,
) -> tuple[StockLevel, StockMovement]:
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    level = _get_locked_stock_level(variant)
    level.quantity_available += quantity
    level.save()
    movement = StockMovement.objects.create(
        variant=variant,
        movement_type=MovementType.RETURN,
        quantity=quantity,
        quantity_after=level.quantity_available,
        notes=notes,
        performed_by=performed_by,
    )
    return level, movement
