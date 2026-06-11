"""Berechnung der Verkäuferbewertung.

Logik (steigt/sinkt nachvollziehbar):
  base   = Bayes-Mittel der Sternebewertungen — robust gegen einzelne Ausreißer
  + Bonus für abgeschlossene Verkäufe (etablierte Verkäufer)
  − Strafe für Beschwerden (DSA-Meldungen gegen Lose des Verkäufers)
Nur freigegebene (status='approved') Reviews zählen → Schutz vor Fakes.
"""
from app import db
from app.models.review import Review
from app.models.auction import Auction
from app.models.report import Report

PRIOR_MEAN = 4.0      # Start-Annahme (neutral-positiv)
PRIOR_WEIGHT = 5      # wie stark der Prior wirkt (entspricht 5 fiktiven Reviews)


def _clamp(v, lo=0.0, hi=5.0):
    return max(lo, min(hi, v))


def recompute_seller_rating(seller_id):
    """Aktualisiert User.rating und review_count für den Verkäufer."""
    from app.models.user import User
    seller = db.session.get(User, seller_id)
    if not seller:
        return

    reviews = Review.query.filter_by(seller_id=seller_id, status='approved').all()
    n = len(reviews)
    total = sum(r.stars for r in reviews)
    base = (PRIOR_WEIGHT * PRIOR_MEAN + total) / (PRIOR_WEIGHT + n)

    # Bonus für abgeschlossene Verkäufe
    sales = Auction.query.filter_by(seller_id=seller_id, is_active=False, is_confirmed=True).count()
    sales_bonus = min(0.25, 0.01 * sales)

    # Strafe für Beschwerden gegen Lose dieses Verkäufers
    complaints = (db.session.query(Report)
                  .join(Auction, Report.auction_id == Auction.id)
                  .filter(Auction.seller_id == seller_id)
                  .count())
    complaint_penalty = min(1.5, 0.2 * complaints)

    seller.rating = round(_clamp(base + sales_bonus - complaint_penalty), 2)
    seller.review_count = n
    db.session.commit()
    return seller.rating
